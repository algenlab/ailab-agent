"""Generate solution variants and tracker code."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_client import LLMJsonError, chat_json

from algolab.schemas.input import ProblemInput
from algolab.schemas.correctness import CorrectnessContract
from algolab.schemas.semantic_trace import SolutionVariant
from algolab.schemas.validation import BuildArtifact
from algolab.schemas.visual_plan import VisualPlan
from algolab.generation.repair import build_solution_repair_prompt
from algolab.verification.repair_context import build_repair_context


PROMPT_DIR = Path(__file__).parent / "prompts"


def _prompt_text(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def _chat_json(system_prompt: str, user_prompt: str, *, kind: str) -> dict[str, Any]:
    try:
        return chat_json(system_prompt, user_prompt, kind=kind)
    except TypeError as exc:
        if "unexpected keyword argument" in str(exc) and "kind" in str(exc):
            return chat_json(system_prompt, user_prompt)
        raise


def _build_user_prompt(request: ProblemInput) -> str:
    input_json = json.dumps(request.input_data, ensure_ascii=False, separators=(",", ":"))
    parts = [
        "题目：",
        request.problem,
        "",
        "具体输入 JSON：",
        input_json,
        "",
        f"希望生成解法数量：{request.solution_count}",
        "",
        "生成规模要求：",
        f"- variants 数量必须严格等于 {request.solution_count}。",
        "- 每个解法只保留教学必要步骤，trace 通常控制在 6-12 个关键事件。",
        "- reason 使用简短简体中文，单条尽量不超过 35 个字。",
        "- state 只保留当前可视化必要变量，不要反复塞入无关大对象。",
        "- 不要输出额外说明、markdown 或无关字段。",
    ]
    if request.strategy_hint:
        parts.extend(["", "用户指定或偏好的解法思路：", request.strategy_hint])
    if request.user_code:
        parts.extend(["", "用户提供代码，可作为一个解法变体进行插桩：", request.user_code])
    if request.expected_result is not None:
        parts.extend(["", "用户给出的期望输出：", json.dumps(request.expected_result, ensure_ascii=False)])
    domain_hints = _domain_specific_generation_hints(request)
    if domain_hints:
        parts.extend(["", "固定短模板要求：", *domain_hints])
    return "\n".join(parts)


def _domain_specific_generation_hints(request: ProblemInput) -> list[str]:
    text = "\n".join([request.problem or "", request.strategy_hint or ""]).lower()
    hints: list[str] = []
    if any(token in text for token in ("闭区间二分", "二分查找", "binary search", "binary_search")) and "二分图" not in text:
        hints.extend(
            [
                "- 闭区间二分固定短模板：while left <= right，每轮 mid=(left+right)//2，先 compare nums[mid] 与 target，再 move pointer:left 或 pointer:right。",
                "- compare 的 state 使用移动前窗口；move 的前一个事件必须是 compare，不要在 compare 和 move 之间插入 explain/set/mark。",
                "- move pointer:left/right 后 state.mid 必须等于新窗口 (left+right)//2；若新区间为空则不要发布 mid 字段，不要把 mid 置为 None。",
                "- 每个 pointer:left/right move 必须带 value、deps 或 before/after；value 写新指针位置，before/after 写旧窗口和新窗口，deps 指向上一帧 compare 的 nums[mid] 或 pointer:mid。",
                "- targets/deps 覆盖 pointer:left、pointer:right、pointer:mid 和 nums[mid]；reason 写清 nums[mid] < target 或 > target 的收缩依据。",
            ]
        )
    if any(token in text for token in ("划分成两个", "0-1 背包", "0_1 背包", "01 背包", "subset sum", "subset-sum", "等和划分")):
        hints.extend(
            [
                "- 0-1 背包固定短模板：subset-sum 使用 target=sum(nums)//2，dp[0]=True，capacity_index 必须倒序扫描。",
                "- 初始化必须 tracer.create(\"dp\", state={...})，state.dp[0]=True 且 state.dp_contract 存在；不要只用 tracer.set(\"dp[0]\") 做 base case。",
                "- dp_contract.expected_targets 只列实际 tracer.set 的 dp 单元和最终答案 target；不要列出没有事件覆盖的 dp[2]/dp[3]/dp[4] 等全表容量。",
                "- 每个 tracer.set(\"dp[c]\") 都带 deps=[\"dp[c]\",\"dp[c-weight]\",\"nums[i]\"]、i、capacity_index、capacity、old_value、candidate、formula。",
                "- subset-sum 每个 DP 事件的 state 保留 nums、target 和当前 nums[i]；reason/teaching 提到 nums 或元素时，targets/deps/state 必须有 nums 证据。",
            ]
        )
    if any(token in text for token in ("bitmask_subsets", "bitmask subsets", "bitmask subset", "位掩码", "二进制掩码", "掩码枚举", "所有子集", "子集枚举", "subsets")):
        hints.extend(
            [
                "- 位掩码子集固定短模板：用 tracer.create(\"subsets\") 初始化结果容器，state.subsets=[]，state.mask=0。",
                "- 每个 mask 先 tracer.set(\"mask\") 写当前掩码，再 tracer.set(\"subset\") 展示当前子集；subset 事件带 value=current_subset、deps=[\"mask\"]、state。",
                "- 把累计结果写回 tracer.set(\"subsets\")，value=accumulated_subsets；也可以把 tracer.set(\"subsets\") 的 deps 改为 [\"mask\"]，不要使用 res[i]/result[i] 作为 target/deps。",
                "- deps 写 subset 时同一事件 state.subset 必须存在；deps 写 subsets 时同一事件 state.subsets 必须存在，最终 answer state 同时保留 subsets 和 answer。",
                "- 最终用 tracer.mark(\"answer\")，value=subsets，role=\"answer\"，deps=[\"subsets\"]，state.answer=subsets；不要把 res[1]、result[1] 或 answer[1] 放进 targets。",
            ]
        )
    if any(token in text for token in ("bounded_knapsack", "多重背包", "数量上限", "counts")):
        hints.extend(
            [
                "- 多重背包固定短模板：使用 dp_contract.subfamily=\"bounded_knapsack\"，state 保留 i、capacity_index、capacity、take/count、old_value、candidate、formula。",
                "- 每个 tracer.set(\"dp[c]\") 的 value 必须等于当前 candidate 或该容量最终最大值，deps 指向 dp[c-take*weight]、weights[i]、values[i]、counts[i]。",
                "- 可以先展示同一容量的增量 candidate，再展示最终 max；最终答案必须是 dp[capacity]，并调用 tracer.result(dp[capacity])。",
                "- 所有事件 reason 非空，create/set/compare/mark 都写简短原因，不能用空字符串。",
            ]
        )
    if any(token in text for token in ("lcs", "lcs_length", "最长公共子序列", "公共子序列")):
        hints.extend(
            [
                "- LCS 固定短模板：使用 dp_contract.subfamily=\"lcs\"，二维 dp[i][j] 表示 text1 前 i 个字符与 text2 前 j 个字符的 LCS 长度。",
                "- LCS base row/column 的 0 值只放在 tracer.create(\"dp\") 的 state.dp；不要把 dp[0][j] 或 dp[i][0] 放进 dp_contract.expected_targets，除非真的逐格 tracer.set。",
                "- expected_targets 只列真实 tracer.set 的 dp[i][j] 和最终答案 dp[len(text1)][len(text2)]，不要列只由初始化 create 覆盖的 base cell。",
                "- 每个 tracer.set(\"dp[i][j]\") 的 state 保留 text1、text2、i、j、current、old_value、formula 和 dp_contract。",
                "- deps=[\"dp[i-1][j]\", \"dp[i][j-1]\", \"dp[i-1][j-1]\", \"text1[i-1]\", \"text2[j-1]\"]；匹配时 formula 写 dp[i][j]=dp[i-1][j-1]+1，否则写 max(dp[i-1][j], dp[i][j-1])。",
                "- 最终 role=answer 事件引用 dp[len(text1)][len(text2)]，trace.result 等于该单元值。",
            ]
        )
    if any(token in text for token in ("最长无重复", "无重复子串", "string_sliding_window", "sliding window", "window_counts")):
        hints.extend(
            [
                "- 字符串滑动窗口固定短模板：这是单串 text 算法，family_contract={\"family\":\"string\",\"submode\":\"string_sliding_window\"}，不要添加 pattern。",
                "- state 保留 text、left、right、window_counts、best；扩展用 pointer:right，收缩用 pointer:left。",
                "- 每个 move/set/answer 事件 targets 或 deps 必须引用 text[i]、pointer:left 或 pointer:right；reason 写窗口扩展/收缩原因。",
                "- 遇到重复字符时按 while window_counts[text[right]] > 1 先收缩到无重复再更新 best；每次收缩都 set window_counts 并 move pointer:left。",
                "- 每个事件的 window_counts 必须等于 text[left:right+1] 的逐字符计数；不要把收缩后的 window_counts 配上收缩前的 left/right。",
                "- 不要发布含重复字符的 state.window_counts；若需要解释重复，使用 pending_char/pending_count，发布事件 state.window_counts 必须已完成收缩。",
                "- 如果必须发布重复帧，reason 或 state.phase 写 duplicate_before_shrink/重复/收缩，且该重复帧的 window_counts 仍必须与当前 left/right 完全一致。",
                "- answer 事件 deps/targets 引用 text 或 pointer，不要只 mark answer。",
            ]
        )
    if any(token in text for token in ("z algorithm", "z_algorithm", "z 算法", "z数组", "z 数组")):
        hints.extend(
            [
                "- Z Algorithm 固定短模板：family_contract={\"family\":\"string\",\"submode\":\"z_algorithm\",\"expected_tables\":[\"z\"]}，state 保留 text、z、i、l/r 或 left/right。",
                "- 写 z[i] 前必须完成 Z-box 复用和 while 扩展，不要在扩展完成前 tracer.set(\"z[i]\") 写半成品。",
                "- text=\"aabcaabx\" 的标准 z 是 [0,1,0,0,3,1,0,0]，特别是 z[4]=3；样例 i=4 先 compare text[0]/text[4]、text[1]/text[5]、text[2]/text[6]，扩展完成后再 tracer.set(\"z[4]\", value=3)。",
            ]
        )
    if any(token in text for token in ("jump_game", "jump game", "跳跃游戏")):
        hints.extend(
            [
                "- 跳跃游戏贪心固定短模板：state.greedy_contract={\"submode\":\"jump_game\"}，每步保留 nums、i、previous_reach、candidate_reach、reach。",
                "- 正常可达步 reach=max(previous_reach, i+nums[i])，candidate_reach=i+nums[i]；deps 指向 nums[i] 和 reach。",
                "- i > previous_reach 时立即 role=\"answer\" 且 value=False，state.answer=False 后停止 trace；不要继续扫描不可达下标，也不要用不可达下标更新 reach。",
                "- 初始化 create 可以用 i=-1、reach=0 表示尚未扫描；第一个扫描事件若 i=0，必须写 previous_reach=0、candidate_reach=nums[0]、reach=nums[0]。不可达样例中 state.i=2 只能出现在最终 answer=False 帧。",
            ]
        )
    if any(token in text for token in ("bfs", "最短边数", "最短层数", "队列按层", "首次访问")):
        hints.extend(
            [
                "- BFS 固定短模板：create queue/dist/parent，pop current，compare edge:current->neighbor，再首次访问 neighbor。",
                "- first_visit 必须用 tracer.set(\"dist[neighbor]\")，完整写法为 tracer.set(\"dist[neighbor]\", value=dist[current]+1, role=\"visited\", deps=[\"node:current\", \"node:neighbor\", \"edge:current->neighbor\"], state={...})；不要只写 deps=[\"dist[current]\", \"edge:current->neighbor\"]，不要只 push queue。",
                "- 同一 first_visit state 必须设置 parent[neighbor]=current，dist[neighbor]=dist[current]+1；不要写 parent[neighbor]=neighbor。",
                "- state 必须同时保留 current、neighbor、queue、dist、parent 和 graph_contract；push queue 的 value 是 neighbor。",
            ]
        )
    if any(token in text for token in ("zero_one_bfs", "0-1 bfs", "0_1_bfs", "01_bfs", "0/1 权", "0/1权")):
        hints.extend(
            [
                "- 0-1 BFS 固定短模板：graph_contract={\"submode\":\"zero_one_bfs\"}，state 保留 weighted_graph、deque、dist、parent、current、neighbor、edge_weight。",
                "- 每条边先 tracer.compare([\"edge:u->v\"], deps=[\"node:u\", \"node:v\", \"edge:u->v\"], state={...}, reason=\"check_edge 0/1 权边\")。",
                "- first_visit/relax 用 tracer.set(\"dist[v]\", value=new_dist, deps=[\"node:u\", \"node:v\", \"edge:u->v\"], state 包含 dist[u]、old_dist、new_dist、edge_weight、parent[v]=u)。",
                "- edge_weight=0 时 push_front，edge_weight=1 时 push_back；push_front/push_back 事件也带 deps=[\"node:u\", \"node:v\", \"edge:u->v\"] 和队首/队尾原因。",
            ]
        )
    if any(token in text for token in ("连通分量", "connected components", "connected_components")):
        hints.extend(
            [
                "- 连通分量固定短模板：优先使用 graph_contract={\"submode\":\"connected_components\"}，state 保留 graph、visited、component、components。",
                "- state.component 只能是当前正在遍历的连通分量；不要把多个 component 合并进 state.component。已完成分量放 state.components；样例 A-B 和 C 必须分成 ['A','B'] 与 ['C']。",
                "- state.components 的每个内层列表也必须是一个连通分量；不要发布 [['A','B','C']] 或把孤立点 C 合并进 ['A','B']。",
                "- 处理样例 A-B + C 时，完成第一块后 state.components=[['A','B']]；开始遍历 C 时重置 state.component=['C']，最终答案才是 components=[['A','B'], ['C']]。",
                "- 如果使用 DFS submode，必须在每个事件 state 中保留 stack 或 frame:dfs frontier，并用 tracer.enter(\"frame:dfs(u)\") / tracer.exit(\"frame:dfs(u)\")。",
                "- 每条 DFS 边先 compare edge:u->v，再 mark/set visited[v]，deps 包含 node:u、node:v、edge:u->v。",
            ]
        )
    if any(token in text for token in ("拓扑", "topological", "topo", "kahn")):
        hints.extend(
            [
                "- 拓扑排序固定短模板：必须使用 Kahn indegree + queue，tracker 只保留 6-10 个 events，不要写成长篇 tracker。",
                "- 拓扑排序 trace 顺序固定为 create graph/indegree、pop queue、decrement indegree、push zero indegree、mark topo_order。",
                "- 每次 decrement indegree[v] 用 tracer.set(\"indegree[v]\", deps=[\"indegree[v]\", \"edge:u->v\"]...)；indegree[v]==0 后立刻 tracer.push(\"queue\", value=v, deps=[\"indegree[v]\", \"edge:u->v\"]...)。",
                "- 最终用 tracer.mark(\"topo_order\", value=topo_order, role=\"answer\", state={...})，必须调用 tracer.result(topo_order) 后 return tracer.to_trace()；不要输出所有无关历史或长注释。",
            ]
        )
    if any(token in text for token in ("差分", "difference array", "range add", "区间加")):
        hints.extend(
            [
                "- 差分数组固定短模板：先按原数组初始化 diff，diff[0]=nums[0]，diff[i]=nums[i]-nums[i-1]。",
                "- 每条 update=[left,right,delta] 只做 diff[left]+=delta；若 right+1 < n，再做 diff[right+1]-=delta。不要把最终数组值写回 diff。",
                "- 每个 tracer.set(\"diff[i]\") 都带 deps、value、state.update_index、state.left/right/delta 和 array_contract.expected_targets。",
                "- 差分数组最终重建必须逐个 tracer.set(\"nums[i]\")，expected_targets 包含 nums[0], nums[1], nums[2]；state 保留 running_sum，deps 指向 diff[i] 或 running_sum，不要只更新 diff。",
            ]
        )
    if any(token in text for token in ("dijkstra", "最短路", "最小堆")):
        hints.extend(
            [
                "- Dijkstra 固定短模板：graph_contract={\"submode\":\"dijkstra\"}，state 保留 weighted_graph、heap、dist、parent、current、neighbor。",
                "- 每条边先 compare edge:u->v；relax 必须用 tracer.set(\"dist[v]\")，deps=[\"node:u\", \"node:v\", \"edge:u->v\", \"dist[u]\"]。",
                "- relax state.current/neighbor、old_dist/new_dist/edge_weight 都必须存在；push heap 也带 node/edge deps。",
            ]
        )
    if any(token in text for token in ("segment_tree", "segment tree", "线段树")):
        hints.extend(
            [
                "- 线段树固定短模板：tracker_code 少于 80 行，只保留 1 个 variant、6-10 个 events，展示 build root/child、一次 query、一次 update 和 answer。",
                "- family_contract={\"family\":\"range_structure\",\"submode\":\"segment_tree\",\"expected_events\":[\"build\",\"query\",\"update\"]}，state.segment_tree.nodes 使用 node:root 等稳定 id。",
                "- 每个 node:<id> target/deps 必须在 state.segment_tree.nodes 中存在；node.meta 保留 l/r/sum，更新后沿叶子到 node:root 同步 sum。",
                "- 线段树 update 后必须沿叶子到 root 同步 sum/value；state.segment_tree.nodes[].meta.sum 必须等于当前 state.nums 区间和，不要只更新叶子或 answer，父区间和 root 必须同步。",
            ]
        )
    if any(token in text for token in ("fenwick", "fenwick_tree", "binary indexed", "树状数组")):
        hints.extend(
            [
                "- 树状数组固定短模板：tracker_code 少于 80 行，只保留 create bit、一次 query 累加、一次 update lowbit 跳转和 answer。",
                "- family_contract={\"family\":\"data_structure\",\"submode\":\"fenwick_tree\",\"expected_events\":[\"build\",\"query\",\"update\"]}，state 保留 nums、bit/fenwick、index、lowbit、answer；更新时先 set nums[pos] 再沿 lowbit set bit[i]。",
                "- bit 必须是 1-indexed 且长度 len(nums)+1；每个 set bit[i] 带 deps、value、lowbit，不要展开成长篇通用 tracker。",
            ]
        )
    if any(token in text for token in ("sparse_table", "sparse table", "稀疏表", "st表", "range min")):
        hints.extend(
            [
                "- Sparse table 超时必须用紧凑固定模板：tracker_code 少于 80 行，只保留 create st、query 两个区间、answer；不要逐格展开所有 st build 事件，create state 写完整 st。",
                "- Sparse table state 必须包含完整正确 st 表；st[0]=nums，st[k][i]=min(st[k-1][i], st[k-1][i+2^(k-1)])。",
                "- nums=[5,2,7,3,6,1] 时 st[1]=[2,2,3,3,1]，st[2]=[2,2,1]；不要发布缺项或错误 st。",
                "- Sparse table target/deps 只能引用当前 state.st 中真实存在的单元；不要引用不存在的 st[2][1]。如果 state.st[2] 长度不足 2，就不能把 st[2][1] 放进 target/deps，必须先在 create state 写完整 st。",
            ]
        )
    if any(token in text for token in ("状态压缩", "state compression", "bitmask tsp", "tsp", "旅行回路")):
        hints.extend(
            [
                "- 状态压缩 TSP 固定短模板：dp[mask][u] 转移保持短 tracker，只展示 base、1-2 个关键转移和最终 ans。",
                "- dp_contract.containers 使用 [\"dp\", \"ans\"]；answer_position=\"ans\"；expected_targets 只列实际 set 的 dp[mask][u] 和 ans。",
                "- 最终必须 tracer.set(\"ans\", value=answer, deps=[\"dp[full_mask][last]\"...], role=\"answer\", state 包含 mask/current/full_mask/formula)，再 tracer.result(answer)。",
            ]
        )
    if any(token in text for token in ("数位 dp", "数位dp", "digit dp", "不含 7", "不含7", "不包含数字 7", "不包含数字7", "逐位处理")):
        hints.extend(
            [
                "- 数位 DP 固定短模板：不包含数字 7 的计数只返回 JSON object，不能把 JSON object 包成字符串。",
                "- 数位 DP tracker_code 少于 80 行，只保留 create dp、set dp[1]、set dp[2]、set ans 四类关键事件；不要写通用递归枚举长 tracker，不要使用九进制转换法。",
                "- 每个 DP set 都必须带 deps、value、state.digit 或 state.pos/current、formula 和 dp_contract。",
                "- 对 n=20 示例必须展示 dp[0]=1、dp[1]=2、dp[2]=18，并最终 tracer.set(\"ans\", value=18, deps=[\"dp[2]\"], role=\"answer\")。",
                "- answer_position=\"ans\" 时 expected_targets 只列实际 set 的 dp 项和 ans；最终必须 tracer.set(\"ans\")，deps 指向最后 dp 状态，role=\"answer\"。",
                "- 不要发布缺 deps 或缺 digit/current 循环变量的 set 事件。",
            ]
        )
    if any(token in text for token in ("全排列", "permutation", "permutations", "排列")):
        hints.extend(
            [
                "- 全排列回溯固定短模板：family_contract={\"family\":\"backtracking\",\"submode\":\"permutations\",\"expected_events\":[\"choose\",\"record\",\"undo\"]}。",
                "- choose 用 tracer.push/mark/enter 表达，undo 用 tracer.pop/unmark/exit 表达，state 每步保留 recursion_tree、path、used、answer。",
                "- record 事件必须 role=\"answer\"，state.answer 包含新排列，deps=[\"path\"]，reason 写 record/记录完整排列。",
                "- frame id 禁止包含空格；不要用 str(path) 生成 frame:dfs([1, 2])，改用 frame:dfs(1_2) 或 frame:dfs(root)。enter 和 exit 必须使用完全相同的 frame id。",
                "- search_tree/recursion_tree 只能有一个 root，所有分支节点通过 edges 连接到已有 root 或 choice/frame 节点。",
            ]
        )
    if any(token in text for token in ("凸包", "convex hull", "convex_hull", "andrew", "单调链", "orientation", "叉积")):
        hints.extend(
            [
                "- 凸包 Andrew 固定短模板：使用 geometry state，包含 geometry.points、geometry.hull/stack、current_point 和 cross，不要使用 backtracking family_contract，也不要设置 family_contract family=geometry。",
                "- compare 带 value=叉积，deps=[\"geometry\"]，reason 写左转/右转/弹出依据；不要在 deps 使用 point:，point:* 只能作为 target/高亮对象。",
                "- 中间候选只放 geometry.stack/current_point/candidate，geometry.hull 只放最终或已验证凸包；最终 hull 顺序必须和 solve/expected answer 一致。",
                "- point id 使用 point:<id>；每个 compare/pop/answer 事件都重复完整 state.geometry.points，同一事件 state.geometry.points 中必须包含被 targets 引用的点，不要只在 create 事件写 points。",
                "- 固定点表写法：geometry_points=[{\"id\":\"p0\",\"x\":0,\"y\":0},...]；point:p0 只能作为 target/高亮对象，deps 固定用 geometry，避免 point deps 无法解析。",
                "- 最终答案 deps 也必须是 [\"geometry\"]；不要在 answer deps 使用 point:。",
            ]
        )
    if any(token in text for token in ("two sum", "two_sum", "两数之和", "哈希表一次遍历")):
        hints.extend(
            [
                "- Two Sum 哈希固定短模板：使用 state.hash_contract={\"submode\":\"two_sum\"}，不要设置 family_contract family=hash。",
                "- 第一帧必须 tracer.create(\"seen\")，state.phase=\"initialization\"，state.seen={}，state.hash_contract={\"submode\":\"two_sum\"}。",
                "- 每轮 state 保留 nums、target、i、value、need、seen；检查命中用 deps=[\"seen[need]\",\"nums[i]\"]。",
                "- 未命中后 set seen[value]，命中后 role=answer，answer 为两个下标。",
            ]
        )
    if any(token in text for token in ("二分图匹配", "bipartite matching", "增广路径", "augmenting path", "最大匹配")):
        hints.extend(
            [
                "- 二分图匹配固定短模板：state 保留 graph、left_nodes、right_nodes、match、visited、augmenting_path。",
                "- 不要设置 graph_contract submode=dfs；若确实设置 DFS contract，就必须给每个事件 stack 或 frame:dfs enter/exit。",
                "- 不要使用裸 frame:dfs；若使用递归帧，frame id 必须带节点，例如 frame:dfs(L1)。每个 tracer.exit 的 target 必须和之前 tracer.enter 完全相同，不能 exit 未进入的 frame；简单匹配过程建议不用 enter/exit。",
                "- 每次成功增广必须同步 match[left]=right 和 match[right]=left，deps 包含 edge:left->right；最终答案只返回左侧点到右侧点的映射。",
                "- 重新匹配时旧反向边必须同步清理：样例中若 L1 从 R1 改到 R2，旧 match[R1]=L1 必须清除或改为 match[R1]=L2，不能保留不一致双向 match。",
            ]
        )
    if any(token in text for token in ("二分图染色", "bipartite coloring", "bipartite_coloring", "染色")):
        hints.extend(
            [
                "- 二分图染色固定短模板：graph_contract 使用 {\"submode\":\"bipartite_coloring\"}，state 保留 graph、queue、color。",
                "- 不要把颜色写进 dist，也不要设置 graph_contract submode=bfs；color[u] 只能是 0/1。",
                "- 每条边先 tracer.compare([\"edge:u->v\", \"color[u]\"])，首次给 v 染色用 tracer.set(\"color[v]\", deps=[\"color[u]\", \"edge:u->v\"], role=\"visited\")。",
            ]
        )
    if any(token in text for token in ("floyd", "warshall", "全源最短")):
        hints.extend(
            [
                "- Floyd 固定短模板：每次改进用 tracer.set(\"dist[i][j]\", deps=[\"dist[i][k]\", \"dist[k][j]\"], state 包含 k/i/j/old_dist/new_dist/formula)。",
                "- 不要把未 set 的 dist[i][j] 放进 expected_targets；expected_targets 必须与实际 tracer.set 的 dist 单元完全一致。",
                "- 最终答案 mark/set 引用 dist，trace.result 必须等于完整 dist 矩阵。",
            ]
        )
    if any(token in text for token in ("bellman_ford", "bellman-ford", "bellman ford")):
        hints.extend(
            [
                "- Bellman-Ford 固定短模板：graph_contract={\"submode\":\"bellman_ford\"}，按轮次检查 edge:u->v 并在变短时 set dist[v]。",
                "- state.graph.nodes 和 state.graph.edges 必须存在；每个 relax/check 事件都重复完整 state.graph，确保 node:A、edge:A->B 可见。",
                "- compare/check edge 事件 deps 可用 edge:u->v 或 graph，relax 写 old_dist/new_dist/edge_weight/iteration。",
            ]
        )
    if any(token in text for token in ("daily_temperatures", "每日温度", "单调栈", "monotonic stack")):
        hints.extend(
            [
                "- 单调栈固定短模板：使用 family_contract={\"family\":\"monotonic_stack\",\"submode\":\"daily_temperatures\"}，不要使用 range_structure/segment_tree/fenwick/sparse_table。",
                "- 每次 pop 后必须 tracer.set(\"answer[i]\", value=current-i, deps=[\"temperatures[i]\", \"temperatures[current]\"])。",
                "- state 保留 temperatures、stack、answer、current_index/current_temp 和 family_contract。",
            ]
        )
    if any(token in text for token in ("reverse_linked_list", "reverse linked list", "反转链表", "链表反转", "迭代反转", "迭代反转法")):
        hints.extend(
            [
                "- 链表反转固定短模板：family_contract={\"family\":\"linked_list\",\"submode\":\"reverse\",\"expected_events\":[\"move_pointer\",\"link_change\"]}，每步保留 linked_list、current、prev、next。",
                "- link_change 事件必须显式改变边：用 tracer.unlink(\"edge:current->old_next\") 表示断开旧 next，用 tracer.link(\"edge:current->prev\") 表示 current.next 指向 prev；同时更新 state.linked_list.nodes[].meta.next 和 edges。",
                "- linked_list.nodes[].meta.next 与 state.linked_list.edges 必须一致；meta.next=\"1\" 时 edges 包含 [\"0\",\"1\"]，反转后 meta.next=\"0\" 时 edges 包含 [\"1\",\"0\"]。",
                "- 尾节点或 prev=None 时不要写 meta.next=\"\"，否则会被校验成 edge:id->；用 JSON null 或省略 next，并且 state.linked_list.edges 不要包含空端点边。",
                "- 每个 tracer.set 必须带 value、deps 或 before/after，或者让 state.linked_list/current/prev/next 发生真实变化；不要用空 set 只改 reason。",
                "- current/prev/next 指针移动用 tracer.move(\"pointer:current\")、tracer.move(\"pointer:prev\") 或 state 变化表达；link_change 用 tracer.link/tracer.unlink。",
                "- 每轮先保存 next_node，再改 current.next；也可称 old_next。link_change 后 prev 必须移动到 old_current；下一轮第一帧 pointer:current 才写 next_node，不要在本轮继续发布旧 current。",
                "- 不要发布半更新链表状态；事件 state 表示动作后的完整一致状态。如果 meta.next 仍是 old_next，就必须保留 edge:current->old_next；如果移除了 edge:current->old_next，就必须同时把 meta.next 改为 null 或 prev。",
                "- 每轮 link/unlink/set 处理的 current 必须仍是 old_current；不要在完成 old_current 的 link_change 前把 current 写成 next_node。第一轮必须从 head/current=0 开始；下一轮第一帧 pointer:current 才写 next_node。",
                "- tracer.move(\"pointer:current\") 是每轮开始帧，state.current 写本轮 old_current，state.next 写 next_node；每个节点只发布一次 pointer:current move。",
                "- 两节点扩展样例 values=[1,2]：第一轮 old_current=\"0\" 时保存 next_node=\"1\"；处理完 old_current=\"0\" 后，下一帧 current 必须是 \"1\"，prev=\"0\"，不要在下一轮 pointer:current frame 继续写 current=\"0\"。",
                "- 三节点样例 values=[1,2,3]：current 帧顺序必须是 \"0\" -> \"1\" -> \"2\"；处理完 old_current=\"1\" 后，下一帧 current 必须是 \"2\"，不要继续写 current=\"1\"。",
            ]
        )
    if any(token in text for token in ("topk_min_heap", "kth_largest", "第 k 大", "第k大", "小顶堆")):
        hints.extend(
            [
                "- 堆 TopK 固定短模板：family_contract={\"family\":\"heap\",\"submode\":\"topk_min_heap\",\"expected_events\":[\"push\",\"pop\"]}。",
                "- 每个 push/pop state 都保留 heap、heap_type=\"min\"、heap_top=heap[0]；最终答案 target 用 heap[0]。",
                "- len(heap)>k 时必须 tracer.pop(\"heap\", value=removed, deps=[\"heap[0]\"], state={...})，不能只记录 push。",
            ]
        )
    if any(token in text for token in ("中序遍历", "inorder")):
        hints.extend(
            [
                "- 树遍历固定短模板：每个 enter/exit/mark 都必须有非空 reason，不能留空字符串。",
                "- state 保留 tree、current、call_stack、return_values/result；exit frame 时说明当前子树返回或已经访问完成。",
            ]
        )
    if any(token in text for token in ("lca", "最近公共祖先", "lowest common ancestor")):
        hints.extend(
            [
                "- LCA/树递归固定短模板：不要使用 graph_contract submode=dfs；使用 family_contract={\"family\":\"tree\",\"submode\":\"lca\"}。",
                "- 每个 enter/exit state 保留 tree、current、p、q、return_value 或 aggregate；state.current 指向当前节点。",
                "- LCA 第一帧必须是 initialization/create 阶段：用 tracer.create(\"tree\")，state.phase=\"initialization\"，state 保留 tree、p、q 和 family_contract。",
                "- 命中 p/q、左右子树各返回一个目标、或向上返回非空节点时，都在 reason 和 return_value 中写清依据；最终 role=answer。",
            ]
        )
    if any(token in text for token in ("trie", "字典树", "前缀统计", "prefix_count")):
        hints.extend(
            [
                "- Trie 前缀统计固定短模板：root.meta.prefix_count=len(words)，每个子节点 meta.prefix_count 等于经过该前缀的单词数。",
                "- 创建新节点必须有显式 create_node 事件：优先 tracer.set(\"node:<id>\", role=\"create_node\", deps=[\"node:<parent>\", \"char:<word_index>:<char_index>\"], state=...)；reason/action 含 create_node/创建新节点，并同步 state.trie.nodes 和 state.trie.edges。",
                "- query 前缀终点 node:<id> 的 meta.prefix_count 必须等于答案；答案 mark value=prefix_count，deps=[\"node:<id>\"]。",
                "- 不要把 root 或未查询节点的 prefix_count 写成 0；每个字符步骤保留 current_char 和 node:<id>。",
                "- words 包含空串时 root 必须 terminal/is_word=True，并发布 terminal 事件：可用 tracer.mark(\"node:root\")，并带 value=True、deps=[\"node:root\"]，state 中 root.meta.terminal=True。",
                "- prefix 为空时答案来自 root.meta.prefix_count=len(words)，直接 mark root；不要把 root prefix_count 写成 0。",
            ]
        )
    if any(token in text for token in ("articulation_bridges", "articulation", "bridges", "割点", "桥", "tarjan")):
        hints.extend(
            [
                "- Tarjan 割点桥固定短模板：graph_contract={\"submode\":\"tarjan\"}，DFS 首次访问节点必须 tracer.set(\"dfn[u]\") 再 tracer.set(\"low[u]\")。",
                "- 第一帧必须是 initialization/create 阶段：用 tracer.create(\"graph\")，state.phase=\"initialization\"，并给出 dfn/low/parent/stack/on_stack 初始化。",
                "- dfn 写入事件和 low 写入事件必须显式存在，state 保留 graph、dfn、low、parent、time、current。",
                "- 发现返祖边或子树返回时更新 low[u]，并添加 component 弹栈事件：state.component 非空且 component 节点已从 stack 移除；桥/割点答案最后 role=answer。",
                "- Tarjan 割点桥所有事件 reason 非空；create/set/compare/mark/enter/exit 和 dfn/low/bridge/articulation/component 事件都写简短 reason。",
                "- 割点/桥最终 answer 事件 target/deps 使用 answer 或 graph，state.articulation 和 state.bridges 保存结果；不要使用 node:articulation 或 node:bridges。",
            ]
        )
    if ("最大独立集" in text or "independent set" in text or "dp_take" in text or "dp_skip" in text) and (
        "树" in text or "tree" in text
    ):
        hints.extend(
            [
                "- 树形 DP 固定短模板：后序 dfs 返回 (take, skip)，先递归完成所有 child，再 set 当前节点两个 DP 状态。",
                "- trace 中不要发布父节点半成品：当前节点所有 child 完成前，state.dp_take/dp_skip 里不要写当前父节点的临时值。",
                "- 每个节点完成后依次 tracer.set(\"dp_take[u]\", value=take, deps=child_deps+[\"node:u\"], state={...}) 和 tracer.set(\"dp_skip[u]\", value=skip, deps=child_deps, state={...})。",
                "- 若使用 family_contract.expected_nodes，所有节点都必须通过 deps 或 targets 引用 node:<id>；enter/exit frame 时 deps=[\"node:u\"]。",
                "- dp_contract.containers 包含 [\"dp_take\",\"dp_skip\",\"answer\"]，answer_position=\"answer\"，expected_targets 包含每个实际 set 的 dp_take/dp_skip 和 answer。",
                "- 最终必须 tracer.set(\"answer\")，value=max(dp_take[root], dp_skip[root])，deps=[\"dp_take[root]\", \"dp_skip[root]\"], role=\"answer\"。",
            ]
        )
    return hints


def generate_solution_spec(request: ProblemInput) -> dict[str, Any]:
    return normalize_solution_spec(_chat_json(_prompt_text("tracker_system.txt"), _build_user_prompt(request), kind="generation"))


def _build_contract_user_prompt(request: ProblemInput) -> str:
    parts = [
        "题目：",
        request.problem,
        "",
        "具体输入 JSON：",
        json.dumps(request.input_data, ensure_ascii=False, separators=(",", ":")),
    ]
    if request.expected_result is not None:
        parts.extend(["", "用户给出的 expected：", json.dumps(request.expected_result, ensure_ascii=False)])
    if request.strategy_hint:
        parts.extend(["", "可选算法思路：", request.strategy_hint])
    parts.extend(
        [
            "",
            "请只返回 correctness-contract-v1 JSON。expected 优先；如果提供 oracle_code，它只能返回题目答案本身。",
        ]
    )
    return "\n".join(parts)


def generate_contract_candidate(request: ProblemInput) -> CorrectnessContract:
    raw = _chat_json(_prompt_text("contract_system.txt"), _build_contract_user_prompt(request), kind="generation")
    return normalize_contract_spec(raw)


def build_contract_with_repair(request: ProblemInput, max_rounds: int = 1) -> tuple[CorrectnessContract, list[dict[str, Any]]]:
    repair_log: list[dict[str, Any]] = []
    raw: Any = None
    last_errors: list[str] = []
    for round_idx in range(max_rounds + 1):
        if round_idx == 0:
            try:
                raw = _chat_json(_prompt_text("contract_system.txt"), _build_contract_user_prompt(request), kind="generation")
            except Exception as exc:
                raw = "{}"
                last_errors = [f"{type(exc).__name__}: {exc}"]
                repair_log.append({"round": round_idx, "status": "failed", "errors": last_errors})
                if round_idx >= max_rounds:
                    break
                raw = repair_contract_candidate(request, raw, last_errors)
                continue
        try:
            contract = normalize_contract_spec(raw)
            from algolab.verification.contract_validator import validate_contract

            report = validate_contract(contract, request)
            if report.release_gate.contract_ready:
                repair_log.append({"round": round_idx, "status": "ok", "errors": []})
                return contract, repair_log
            last_errors = [*report.errors, *report.release_gate.blocking_reasons]
        except Exception as exc:
            last_errors = [f"{type(exc).__name__}: {exc}"]
        repair_log.append({"round": round_idx, "status": "failed", "errors": last_errors})
        if round_idx >= max_rounds:
            break
        raw = repair_contract_candidate(request, raw, last_errors)
    raise ValueError("contract repair failed: " + "; ".join(last_errors))


def repair_contract_candidate(request: ProblemInput, previous: Any, errors: list[str]) -> dict[str, Any]:
    prompt = "\n\n".join(
        [
            _build_contract_user_prompt(request),
            "上一次 contract：",
            previous if isinstance(previous, str) else json.dumps(previous, ensure_ascii=False, indent=2),
            "错误信息：",
            "\n".join(errors),
            "请返回修复后的完整 correctness-contract-v1 JSON。",
        ]
    )
    return _chat_json(_prompt_text("contract_repair_system.txt"), prompt, kind="repair")


def normalize_contract_spec(raw: Any) -> CorrectnessContract:
    if not isinstance(raw, dict):
        raise ValueError(f"Contract 顶层必须是 JSON object，实际为 {type(raw).__name__}")
    data = dict(raw)
    data["schema_version"] = str(data.get("schema_version") or "correctness-contract-v1")
    data["input_schema"] = data.get("input_schema") or {}
    data["output_schema"] = str(data.get("output_schema") or "any")
    data["preconditions"] = _string_list(data.get("preconditions"))
    data["postconditions"] = _string_list(data.get("postconditions"))
    data["oracle_strategy"] = str(data.get("oracle_strategy") or "none")
    data["oracle_code"] = str(data.get("oracle_code") or "")
    data["test_cases"] = data.get("test_cases") or []
    data["metamorphic_relations"] = _string_list(data.get("metamorphic_relations"))
    data["process_invariants"] = _string_list(data.get("process_invariants"))
    return CorrectnessContract.model_validate(data)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def repair_solution_spec(request: ProblemInput, previous: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    repair_context = build_repair_context(errors, request=request, previous=previous)
    prompt = build_solution_repair_prompt(
        request_prompt=_build_user_prompt(request),
        previous=previous,
        errors=errors,
        repair_context=repair_context,
    )
    try:
        return normalize_solution_spec(_chat_json(_prompt_text("repair_system.txt"), prompt, kind="repair"))
    except (LLMJsonError, ValueError) as exc:
        if not isinstance(exc, LLMJsonError) and "LLM 顶层输出必须是 JSON object" not in str(exc):
            raise
        label = "LLMJsonError" if isinstance(exc, LLMJsonError) else "ValueError"
        compact_errors = [*errors, f"{label}: {exc}"]
        compact_context = build_repair_context(compact_errors, request=request, previous=previous)
        compact_prompt = build_solution_repair_prompt(
            request_prompt=_build_user_prompt(request),
            previous=_compact_previous_for_json_retry(previous),
            errors=compact_errors,
            repair_context=compact_context,
        )
        return normalize_solution_spec(_chat_json(_prompt_text("repair_system.txt"), compact_prompt, kind="repair"))


def _compact_previous_for_json_retry(previous: dict[str, Any]) -> dict[str, Any]:
    """Keep enough structure for repair while avoiding another oversized JSON response."""
    compact: dict[str, Any] = {
        "problem_title": str(previous.get("problem_title") or ""),
        "input_contract": str(previous.get("input_contract") or ""),
    }
    variants: list[dict[str, Any]] = []
    for item in previous.get("variants") or []:
        if not isinstance(item, dict):
            continue
        variants.append(
            {
                "id": str(item.get("id") or ""),
                "name": str(item.get("name") or ""),
                "strategy": str(item.get("strategy") or "")[:500],
                "time_complexity": str(item.get("time_complexity") or ""),
                "space_complexity": str(item.get("space_complexity") or ""),
                "code": _truncate_previous_code(str(item.get("code") or "")),
                "tracker_code": _truncate_previous_code(str(item.get("tracker_code") or item.get("trace_code") or "")),
            }
        )
    compact["variants"] = variants[:1]
    verifier_code = str(previous.get("verifier_code") or "")
    if verifier_code:
        compact["verifier_code"] = _truncate_previous_code(verifier_code, limit=1000)
    return compact


def _truncate_previous_code(value: str, *, limit: int = 1600) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n# ... 上轮代码已截断；本轮必须重写短 tracker_code，不能复制长代码。\n"


def generate_visual_plan_candidate(artifact: BuildArtifact, capabilities: dict[str, Any]) -> VisualPlan:
    raw = _chat_json(
        _prompt_text("visual_plan_system.txt"),
        _build_visual_plan_user_prompt(artifact, capabilities),
        kind="generation",
    )
    return normalize_visual_plan_spec(raw)


def normalize_visual_plan_spec(raw: Any) -> VisualPlan:
    if not isinstance(raw, dict):
        raise ValueError(f"VisualPlan 顶层必须是 JSON object，实际为 {type(raw).__name__}")
    data = dict(raw)
    data["schema_version"] = str(data.get("schema_version") or "visual-plan-v1")
    data["mode"] = str(data.get("mode") or "teaching")
    data["stage"] = str(data.get("stage") or "teaching_2d")
    data["metaphor"] = str(data.get("metaphor") or "")
    data["camera"] = data.get("camera") or {}
    data["animation"] = data.get("animation") or {}
    data["teaching"] = data.get("teaching") or {}
    data["layout_preferences"] = data.get("layout_preferences") or {}
    data["baseline_target"] = str(data.get("baseline_target") or "teaching_2d")
    return VisualPlan.model_validate(data)


def _build_visual_plan_user_prompt(artifact: BuildArtifact, capabilities: dict[str, Any]) -> str:
    scene_summary = {
        variant_id: {
            "algorithm": scene.algorithm,
            "frames": len(scene.frames),
            "layouts": sorted(
                {
                    str(obj.meta.get("layout"))
                    for frame in scene.frames
                    for obj in frame.objects
                    if obj.type.value == "container" and obj.meta.get("layout")
                }
            ),
        }
        for variant_id, scene in artifact.scenes.items()
    }
    payload = {
        "problem_title": artifact.problem_title,
        "input_data": artifact.input_data,
        "release_gate": artifact.validation.release_gate.model_dump(),
        "scene_summary": scene_summary,
        "capabilities": capabilities,
    }
    return "基于以下已验证 artifact 摘要输出 visual-plan-v1 JSON：\n" + json.dumps(
        payload, ensure_ascii=False, indent=2
    )


def normalize_solution_spec(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        spec = dict(raw)
    elif isinstance(raw, list):
        spec = {"variants": raw}
    else:
        raise ValueError(f"LLM 顶层输出必须是 JSON object，实际为 {type(raw).__name__}")
    variants = spec.get("variants")
    if isinstance(variants, dict):
        spec["variants"] = [variants]
    elif isinstance(variants, list):
        spec["variants"] = [item for item in variants if isinstance(item, dict)]
    else:
        spec["variants"] = []
    spec["problem_title"] = str(spec.get("problem_title") or "算法可视化实验")
    spec["input_contract"] = str(spec.get("input_contract") or "")
    spec["verifier_code"] = str(spec.get("verifier_code") or "")
    return spec


def parse_variants(spec: dict[str, Any]) -> list[SolutionVariant]:
    variants = []
    for item in spec.get("variants") or []:
        variants.append(
            SolutionVariant(
                id=str(item.get("id") or f"variant_{len(variants)}"),
                name=str(item.get("name") or item.get("id") or f"解法 {len(variants) + 1}"),
                strategy=str(item.get("strategy") or ""),
                time_complexity=str(item.get("time_complexity") or ""),
                space_complexity=str(item.get("space_complexity") or ""),
                code=str(item.get("code") or ""),
                tracker_code=str(item.get("tracker_code") or item.get("trace_code") or ""),
            )
        )
    return variants
