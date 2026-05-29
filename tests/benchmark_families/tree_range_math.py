"""Benchmark cases: tree range math."""

from __future__ import annotations

from tests.benchmark_cases import BenchmarkCase, BenchmarkInput

TWO_SUM_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    seen = {}
    for i, x in enumerate(nums):
        need = target - x
        if need in seen:
            return [seen[need], i]
        seen[x] = i
    return []
"""


TWO_SUM_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    seen = {}
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}, {"id": "seen"}], "state": {"nums": nums, "seen": {}, "target": target}, "reason": "初始化数组和哈希表，哈希表记录数值到下标。", "code_line": 1}]
    result = []
    for i, x in enumerate(nums):
        need = target - x
        deps = [{"id": f"seen[{need}]"}] if need in seen else []
        events.append({"step": len(events), "op": "compare", "targets": [{"id": f"nums[{i}]"}], "deps": deps, "value": {"need": need, "exists": need in seen}, "state": {"nums": nums, "seen": dict(seen), "target": target, "i": i, "need": need}, "role": "candidate", "reason": "检查当前数的互补值是否已经出现。", "code_line": 4})
        if need in seen:
            result = [seen[need], i]
            events.append({"step": len(events), "op": "mark", "targets": [{"id": f"nums[{seen[need]}]"}, {"id": f"nums[{i}]"}], "state": {"nums": nums, "seen": dict(seen), "target": target, "answer": result}, "role": "answer", "reason": "互补值已经在哈希表中，找到答案下标。", "code_line": 5})
            break
        seen[x] = i
        events.append({"step": len(events), "op": "set", "targets": [{"id": f"seen[{x}]"}], "after": i, "state": {"nums": nums, "seen": dict(seen), "target": target, "i": i}, "role": "visited", "reason": "把当前数和下标写入哈希表。", "code_line": 7})
    return {"schema_version": "semantic-trace-v1", "algorithm": "两数之和", "input_data": input_data, "result": result, "pseudocode": ["遍历 nums", "若 target - nums[i] 已出现，则返回两个下标", "否则记录 nums[i]"], "events": events}
"""


TWO_SUM_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    target = input_data["target"]
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
"""


DAILY_TEMPERATURES_CODE = """
def solve(input_data):
    temperatures = input_data["temperatures"]
    answer = [0] * len(temperatures)
    stack = []
    for i, temp in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < temp:
            j = stack.pop()
            answer[j] = i - j
        stack.append(i)
    return answer
"""


DAILY_TEMPERATURES_TRACKER = """
def trace(input_data):
    temperatures = input_data["temperatures"]
    answer = [0] * len(temperatures)
    stack = []
    events = [{"step": 0, "op": "create", "targets": [{"id": "temperatures"}, {"id": "stack"}, {"id": "answer"}], "state": {"temperatures": temperatures, "stack": [], "answer": answer[:], "stack_order": "decreasing"}, "reason": "初始化答案数组和单调递减栈，栈里保存还没找到更暖天的下标。", "code_line": 1}]
    for i, temp in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < temp:
            j = stack.pop()
            events.append({"step": len(events), "op": "pop", "targets": [{"id": "stack"}, {"id": f"temperatures[{j}]"}], "deps": [{"id": f"temperatures[{j}]"}, {"id": f"temperatures[{i}]"}], "state": {"temperatures": temperatures, "stack": stack[:], "answer": answer[:], "stack_order": "decreasing", "i": i}, "role": "candidate", "reason": "当前温度更高，弹出栈顶候选。", "code_line": 5})
            answer[j] = i - j
            events.append({"step": len(events), "op": "set", "targets": [{"id": f"answer[{j}]"}], "deps": [{"id": f"temperatures[{j}]"}, {"id": f"temperatures[{i}]"}], "after": answer[j], "state": {"temperatures": temperatures, "stack": stack[:], "answer": answer[:], "stack_order": "decreasing", "i": i}, "role": "answer", "reason": "当前温度更高，弹出栈顶并写入等待天数。", "code_line": 6})
        stack.append(i)
        events.append({"step": len(events), "op": "push", "targets": [{"id": "stack"}, {"id": f"temperatures[{i}]"}], "state": {"temperatures": temperatures, "stack": stack[:], "answer": answer[:], "stack_order": "decreasing", "i": i}, "role": "current", "reason": "当前下标入栈，继续等待未来更高温度。", "code_line": 8})
    return {"schema_version": "semantic-trace-v1", "algorithm": "每日温度", "input_data": input_data, "result": answer, "pseudocode": ["维护温度单调递减的下标栈", "遇到更高温度时弹栈并写答案"], "events": events}
"""


DAILY_TEMPERATURES_VERIFIER = """
def verify(input_data):
    temperatures = input_data["temperatures"]
    ans = []
    for i, temp in enumerate(temperatures):
        wait = 0
        for j in range(i + 1, len(temperatures)):
            if temperatures[j] > temp:
                wait = j - i
                break
        ans.append(wait)
    return ans
"""


MERGE_SORT_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    return sorted(nums)
"""


MERGE_SORT_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    arr = nums[:]
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}], "state": {"nums": arr[:]}, "reason": "复制原数组，准备排序。", "code_line": 1}]
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        events.append({"step": len(events), "op": "compare", "targets": [{"id": f"nums[{i}]"}], "value": key, "state": {"nums": arr[:], "i": i, "key": key}, "role": "candidate", "reason": "取出当前位置元素，向左寻找插入位置。", "code_line": 3})
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            events.append({"step": len(events), "op": "set", "targets": [{"id": f"nums[{j + 1}]"}], "deps": [{"id": f"nums[{j}]"}], "after": arr[j + 1], "state": {"nums": arr[:], "i": i, "j": j}, "role": "current", "reason": "左侧元素更大，向右移动一格。", "code_line": 5})
            j -= 1
        arr[j + 1] = key
        events.append({"step": len(events), "op": "set", "targets": [{"id": f"nums[{j + 1}]"}], "after": key, "state": {"nums": arr[:], "i": i, "j": j + 1}, "role": "answer", "reason": "把元素放到有序前缀的正确位置。", "code_line": 7})
    return {"schema_version": "semantic-trace-v1", "algorithm": "插入排序", "input_data": input_data, "result": arr, "pseudocode": ["逐步维护有序前缀", "将当前元素插入正确位置"], "events": events}
"""


MERGE_SORT_VERIFIER = """
def verify(input_data):
    return sorted(input_data["nums"])
"""


BINARY_TREE_INORDER_CODE = """
def solve(input_data):
    tree = input_data["tree"]
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {str(v) for _, v in tree["edges"]}
    root = ""
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in targets:
            root = node_id
            break
    result = []
    def dfs(node):
        kids = children.get(node, [])
        if len(kids) >= 1:
            dfs(kids[0])
        result.append(node)
        if len(kids) >= 2:
            dfs(kids[1])
    dfs(root)
    return result
"""


BINARY_TREE_INORDER_TRACKER = """
def trace(input_data):
    tree = input_data["tree"]
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {str(v) for _, v in tree["edges"]}
    root = ""
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in targets:
            root = node_id
            break
    tracer = Tracer(input_data, algorithm="二叉树中序遍历", pseudocode=["递归左子树", "访问当前节点", "递归右子树"], policy="full", max_events=180)
    result = []
    call_stack = []
    return_values = {}
    tracer.create("tree", state={"tree": tree, "current": root, "call_stack": call_stack[:], "return_values": dict(return_values), "result": result[:]}, reason="展示二叉树，准备从根节点开始中序遍历。", code_line=1)
    def dfs(node):
        call_stack.append(node)
        frame = f"frame:inorder({node})"
        tracer.enter(
            frame,
            deps=[f"node:{node}"],
            state={"tree": tree, "current": node, "call_stack": call_stack[:], "return_values": dict(return_values), "result": result[:]},
            role="current",
            reason="进入当前节点的递归 frame，准备按左-根-右顺序处理。",
            code_line=5,
        )
        kids = children.get(node, [])
        if len(kids) >= 1:
            dfs(kids[0])
        result.append(node)
        tracer.mark(
            f"node:{node}",
            deps=[frame],
            state={"tree": tree, "current": node, "call_stack": call_stack[:], "return_values": dict(return_values), "result": result[:]},
            role="visited",
            reason="中序遍历在左子树返回后访问当前节点。",
            code_line=8,
        )
        if len(kids) >= 2:
            dfs(kids[1])
        return_values[node] = result[:]
        tracer.exit(
            frame,
            deps=[f"node:{node}"],
            state={"tree": tree, "current": node, "call_stack": call_stack[:], "return_values": dict(return_values), "result": result[:]},
            role="current",
            reason="当前节点子树遍历完成，记录该子树返回值并退出 frame。",
            code_line=11,
        )
        call_stack.pop()
    dfs(root)
    tracer.mark("tree", state={"tree": tree, "current": root, "call_stack": [], "return_values": dict(return_values), "answer": result[:]}, role="answer", reason="根节点 frame 返回后得到完整中序遍历序列。", code_line=12)
    tracer.result(result)
    return tracer.to_trace()
"""


BINARY_TREE_INORDER_VERIFIER = """
def verify(input_data):
    tree = input_data["tree"]
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {str(v) for _, v in tree["edges"]}
    root = ""
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in targets:
            root = node_id
            break
    result = []
    def dfs(node):
        kids = children.get(node, [])
        if len(kids) >= 1:
            dfs(kids[0])
        result.append(node)
        if len(kids) >= 2:
            dfs(kids[1])
    dfs(root)
    return result
"""


LCA_CODE = """
def solve(input_data):
    tree = input_data["tree"]
    p = str(input_data["p"])
    q = str(input_data["q"])
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {v for _, v in tree["edges"]}
    root = ""
    target_ids = {str(x) for x in targets}
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in target_ids:
            root = node_id
            break
    def dfs(node):
        if node == p or node == q:
            return node
        hits = []
        for child in children.get(node, []):
            got = dfs(child)
            if got is not None:
                hits.append(got)
        if len(hits) >= 2:
            return node
        return hits[0] if hits else None
    return dfs(root)
"""


LCA_TRACKER = """
def trace(input_data):
    tree = input_data["tree"]
    p = str(input_data["p"])
    q = str(input_data["q"])
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {str(v) for _, v in tree["edges"]}
    root = ""
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in targets:
            root = node_id
            break
    tracer = Tracer(input_data, algorithm="二叉树最近公共祖先", pseudocode=["后序 DFS", "若左右子树都命中目标，当前节点是 LCA"], policy="full", max_events=180)
    call_stack = []
    return_values = {}
    tracer.create("tree", state={"tree": tree, "p": p, "q": q, "current": root, "call_stack": call_stack[:], "return_values": dict(return_values)}, reason="展示二叉树和两个目标节点。", code_line=1)
    def dfs(node):
        call_stack.append(node)
        frame = f"frame:lca({node})"
        tracer.enter(
            frame,
            deps=[f"node:{node}"],
            state={"tree": tree, "p": p, "q": q, "current": node, "call_stack": call_stack[:], "return_values": dict(return_values)},
            role="current",
            reason="进入当前节点 frame，递归检查当前子树是否包含目标节点。",
            code_line=8,
        )
        if node == p or node == q:
            return_values[node] = node
            tracer.exit(
                frame,
                deps=[f"node:{node}"],
                state={"tree": tree, "p": p, "q": q, "current": node, "call_stack": call_stack[:], "return_values": dict(return_values)},
                role="answer",
                reason="当前节点就是目标节点之一，向父 frame 返回命中节点。",
                code_line=9,
            )
            call_stack.pop()
            return node
        hits = []
        for child in children.get(node, []):
            got = dfs(child)
            if got is not None:
                hits.append(got)
        if len(hits) >= 2:
            return_values[node] = node
            tracer.set(
                f"return_values[{node}]",
                value=node,
                deps=[f"frame:lca({child})" for child in children.get(node, [])] + [f"node:{node}"],
                state={"tree": tree, "p": p, "q": q, "current": node, "call_stack": call_stack[:], "return_values": dict(return_values), "lca": node},
                role="answer",
                reason="左右子树分别返回目标命中，当前节点就是最近公共祖先。",
                code_line=17,
            )
            tracer.exit(frame, deps=[f"node:{node}"], state={"tree": tree, "p": p, "q": q, "current": node, "call_stack": call_stack[:], "return_values": dict(return_values), "lca": node}, role="answer", reason="当前 LCA frame 聚合完成并返回。", code_line=17)
            call_stack.pop()
            return node
        result = hits[0] if hits else None
        return_values[node] = result
        tracer.exit(
            frame,
            deps=[f"node:{node}"],
            state={"tree": tree, "p": p, "q": q, "current": node, "call_stack": call_stack[:], "return_values": dict(return_values)},
            role="current",
            reason="当前子树完成后序聚合，把命中结果返回给父 frame。",
            code_line=18,
        )
        call_stack.pop()
        return result
    answer = dfs(root)
    tracer.mark(f"node:{answer}", deps=[f"frame:lca({root})"], state={"tree": tree, "p": p, "q": q, "current": answer, "call_stack": [], "return_values": dict(return_values), "lca": answer}, role="answer", reason="最近公共祖先已经由根 frame 返回，标记答案节点。", code_line=19)
    tracer.result(answer)
    return tracer.to_trace()
"""


LCA_VERIFIER = """
def verify(input_data):
    tree = input_data["tree"]
    p = str(input_data["p"])
    q = str(input_data["q"])
    parent = {}
    nodes = {str(node["id"]) for node in tree["nodes"]}
    for u, v in tree["edges"]:
        parent[str(v)] = str(u)
    ancestors = set()
    cur = p
    while cur in nodes:
        ancestors.add(cur)
        if cur not in parent:
            break
        cur = parent[cur]
    cur = q
    while cur not in ancestors:
        cur = parent[cur]
    return cur
"""


KTH_LARGEST_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    k = input_data["k"]
    import heapq
    heap = []
    for x in nums:
        heapq.heappush(heap, x)
        if len(heap) > k:
            heapq.heappop(heap)
    return heap[0]
"""


KTH_LARGEST_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    k = input_data["k"]
    import heapq
    heap = []
    contract = {"family": "heap", "submode": "topk_min_heap", "expected_events": ["push"]}
    events = [{"step": 0, "op": "create", "targets": [{"id": "nums"}, {"id": "heap"}], "state": {"nums": nums, "heap": [], "heap_type": "min", "k": k, "family_contract": contract}, "reason": "维护容量为 k 的小顶堆。", "code_line": 1}]
    for i, x in enumerate(nums):
        heapq.heappush(heap, x)
        events.append({"step": len(events), "op": "push", "targets": [{"id": "heap"}, {"id": f"nums[{i}]"}], "state": {"nums": nums, "heap": heap[:], "heap_type": "min", "k": k, "i": i, "heap_top": heap[0], "family_contract": contract}, "role": "current", "reason": "把当前元素加入小顶堆。", "code_line": 5})
        if len(heap) > k:
            removed = heapq.heappop(heap)
            events.append({"step": len(events), "op": "pop", "targets": [{"id": "heap"}], "value": removed, "state": {"nums": nums, "heap": heap[:], "heap_type": "min", "k": k, "i": i, "heap_top": heap[0] if heap else None, "family_contract": contract}, "role": "conflict", "reason": "堆超过 k 个元素，弹出最小值，保留最大的 k 个。", "code_line": 7})
    answer = heap[0]
    events.append({"step": len(events), "op": "mark", "targets": [{"id": "heap[0]"}], "state": {"nums": nums, "heap": heap[:], "heap_type": "min", "k": k, "heap_top": answer, "answer": answer, "family_contract": contract}, "role": "answer", "reason": "堆顶就是第 k 大元素。", "code_line": 8})
    return {"schema_version": "semantic-trace-v1", "algorithm": "数组中的第 K 个最大元素", "input_data": input_data, "result": answer, "pseudocode": ["维护大小为 k 的小顶堆", "堆顶是当前第 k 大"], "events": events}
"""


KTH_LARGEST_VERIFIER = """
def verify(input_data):
    return sorted(input_data["nums"], reverse=True)[input_data["k"] - 1]
"""


TRIE_PREFIX_CODE = """
def solve(input_data):
    words = input_data["words"]
    prefix = input_data["prefix"]
    count = 0
    for word in words:
        if word.startswith(prefix):
            count += 1
    return count
"""


TRIE_PREFIX_TRACKER = """
def trace(input_data):
    words = input_data["words"]
    prefix = input_data["prefix"]
    contract = {"family": "trie", "submode": "prefix_count", "expected_events": ["create_node", "terminal", "prefix_count"]}
    trie = {"nodes": [{"id": "root", "label": "root", "meta": {"count": 0}}], "edges": []}
    children = {"root": {}}
    node_meta = {"root": {"count": 0, "terminal": False}}
    events = [{"step": 0, "op": "create", "targets": [{"id": "trie"}], "state": {"trie": trie, "words": words, "prefix": prefix, "family_contract": contract}, "reason": "初始化 Trie 根节点。", "code_line": 1}]
    for word in words:
        cur = "root"
        node_meta[cur]["count"] += 1
        trie["nodes"][0]["meta"] = dict(node_meta[cur])
        for ch in word:
            if ch not in children[cur]:
                nxt = f"{cur}_{ch}_{len(trie['nodes'])}"
                children[cur][ch] = nxt
                children[nxt] = {}
                node_meta[nxt] = {"count": 0, "terminal": False}
                trie["nodes"].append({"id": nxt, "label": ch, "meta": dict(node_meta[nxt])})
                trie["edges"].append([cur, nxt])
                events.append({"step": len(events), "op": "link", "targets": [{"id": f"node:{nxt}"}], "deps": [{"id": f"node:{cur}"}], "state": {"trie": {"nodes": [dict(node) for node in trie["nodes"]], "edges": trie["edges"][:]}, "words": words, "prefix": prefix, "char": ch, "prefix_count": 0, "family_contract": contract}, "role": "current", "reason": "插入单词时创建新的 Trie 节点。", "code_line": 8})
            cur = children[cur][ch]
            node_meta[cur]["count"] += 1
            for node in trie["nodes"]:
                if node["id"] == cur:
                    node["meta"] = dict(node_meta[cur])
                    break
        node_meta[cur]["terminal"] = True
        for node in trie["nodes"]:
            if node["id"] == cur:
                node["meta"] = dict(node_meta[cur])
                break
    count = sum(1 for word in words if word.startswith(prefix))
    events.append({"step": len(events), "op": "mark", "targets": [{"id": "trie"}], "state": {"trie": trie, "words": words, "prefix": prefix, "prefix_count": count, "answer": count, "family_contract": contract}, "role": "answer", "reason": "统计以给定前缀开头的单词数量。", "code_line": 13})
    return {"schema_version": "semantic-trace-v1", "algorithm": "Trie 前缀计数", "input_data": input_data, "result": count, "pseudocode": ["把单词插入 Trie", "沿前缀路径统计匹配单词"], "events": events}
"""


TRIE_PREFIX_VERIFIER = """
def verify(input_data):
    return sum(1 for word in input_data["words"] if word.startswith(input_data["prefix"]))
"""


PROVINCES_CODE = """
def solve(input_data):
    is_connected = input_data["isConnected"]
    n = len(is_connected)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i in range(n):
        for j in range(i + 1, n):
            if is_connected[i][j]:
                parent[find(i)] = find(j)
    return len({find(i) for i in range(n)})
"""


PROVINCES_TRACKER = """
def trace(input_data):
    is_connected = input_data["isConnected"]
    n = len(is_connected)
    parent = {str(i): str(i) for i in range(n)}
    def find(x):
        while parent[str(x)] != str(x):
            x = int(parent[str(x)])
        return str(x)
    events = [{"step": 0, "op": "create", "targets": [{"id": "union_find"}], "state": {"isConnected": is_connected, "union_find": {"parent": dict(parent)}}, "reason": "每个城市先作为独立集合。", "code_line": 1}]
    for i in range(n):
        for j in range(i + 1, n):
            if is_connected[i][j]:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
                    events.append({"step": len(events), "op": "link", "targets": [{"id": f"node:{ri}"}], "deps": [{"id": f"node:{rj}"}], "state": {"isConnected": is_connected, "union_find": {"parent": dict(parent)}, "i": i, "j": j}, "role": "current", "reason": "两个城市直接相连，合并它们所在集合。", "code_line": 12})
    answer = len({find(i) for i in range(n)})
    events.append({"step": len(events), "op": "mark", "targets": [{"id": "union_find"}], "state": {"isConnected": is_connected, "union_find": {"parent": dict(parent)}, "answer": answer}, "role": "answer", "reason": "根节点数量就是省份数量。", "code_line": 14})
    return {"schema_version": "semantic-trace-v1", "algorithm": "省份数量", "input_data": input_data, "result": answer, "pseudocode": ["每个城市初始化为独立集合", "相连城市执行 union", "统计集合根数量"], "events": events}
"""


PROVINCES_VERIFIER = """
def verify(input_data):
    g = input_data["isConnected"]
    n = len(g)
    seen = [False] * n
    def dfs(i):
        seen[i] = True
        for j, ok in enumerate(g[i]):
            if ok and not seen[j]:
                dfs(j)
    count = 0
    for i in range(n):
        if not seen[i]:
            count += 1
            dfs(i)
    return count
"""


TREE_DIAMETER_CODE = """
def solve(input_data):
    tree = input_data["tree"]
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {str(v) for _, v in tree["edges"]}
    root = ""
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in targets:
            root = node_id
            break
    best = 0
    def dfs(node):
        nonlocal best
        heights = []
        for child in children.get(node, []):
            heights.append(dfs(child))
        heights.sort(reverse=True)
        best = max(best, sum(heights[:2]))
        return 1 + (heights[0] if heights else 0)
    dfs(root)
    return best
"""


TREE_DIAMETER_TRACKER = """
def trace(input_data):
    tree = input_data["tree"]
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {str(v) for _, v in tree["edges"]}
    root = ""
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in targets:
            root = node_id
            break
    tracer = Tracer(input_data, algorithm="二叉树直径", pseudocode=["后序计算每个子树高度", "用最大的两个子树高度更新直径"], policy="full", max_events=180)
    call_stack = []
    height = {}
    diameter = {}
    return_values = {}
    tracer.create("tree", state={"tree": tree, "current": root, "call_stack": call_stack[:], "height": dict(height), "diameter": dict(diameter), "return_values": dict(return_values)}, reason="展示树结构，准备后序聚合子树高度。", code_line=1)
    def dfs(node):
        call_stack.append(node)
        frame = f"frame:diameter({node})"
        tracer.enter(frame, deps=[f"node:{node}"], state={"tree": tree, "current": node, "call_stack": call_stack[:], "height": dict(height), "diameter": dict(diameter), "return_values": dict(return_values)}, role="current", reason="进入节点 frame，先递归计算子树高度。", code_line=7)
        child_heights = []
        for child in children.get(node, []):
            child_heights.append(dfs(child))
        ordered = sorted(child_heights, reverse=True)
        height[node] = 1 + (ordered[0] if ordered else 0)
        best_child = 0
        for child in children.get(node, []):
            best_child = max(best_child, diameter.get(child, 0))
        diameter[node] = max(best_child, sum(ordered[:2]))
        return_values[node] = height[node]
        child_deps = [f"frame:diameter({child})" for child in children.get(node, [])] or [f"node:{node}"]
        tracer.set(
            f"diameter[{node}]",
            value=diameter[node],
            deps=child_deps + [f"node:{node}"],
            state={"tree": tree, "current": node, "call_stack": call_stack[:], "height": dict(height), "diameter": dict(diameter), "return_values": dict(return_values)},
            role="answer" if node == root else "current",
            reason="根据两个最大子树高度和子树已有直径做子树聚合，更新树直径。",
            code_line=13,
        )
        tracer.exit(frame, deps=[f"node:{node}"], state={"tree": tree, "current": node, "call_stack": call_stack[:], "height": dict(height), "diameter": dict(diameter), "return_values": dict(return_values)}, role="current", reason="当前节点返回子树高度给父 frame。", code_line=14)
        call_stack.pop()
        return height[node]
    dfs(root)
    answer = diameter[root]
    tracer.mark(f"node:{root}", deps=[f"frame:diameter({root})"], state={"tree": tree, "current": root, "call_stack": [], "height": dict(height), "diameter": dict(diameter), "return_values": dict(return_values), "answer": answer}, role="answer", reason="根节点聚合完成，得到整棵树直径。", code_line=15)
    tracer.result(answer)
    return tracer.to_trace()
"""


TREE_DIAMETER_VERIFIER = """
def verify(input_data):
    tree = input_data["tree"]
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {str(v) for _, v in tree["edges"]}
    root = ""
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in targets:
            root = node_id
            break
    best = 0
    def dfs(node):
        nonlocal best
        heights = []
        for child in children.get(node, []):
            heights.append(dfs(child))
        heights.sort(reverse=True)
        best = max(best, sum(heights[:2]))
        return 1 + (heights[0] if heights else 0)
    dfs(root)
    return best
"""


TREE_MAX_INDEPENDENT_SET_CODE = """
def solve(input_data):
    tree = input_data["tree"]
    weights = {str(node["id"]): int(node.get("value", node.get("weight", 1))) for node in tree["nodes"]}
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {str(v) for _, v in tree["edges"]}
    root = ""
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in targets:
            root = node_id
            break
    def dfs(node):
        take = weights[node]
        skip = 0
        for child in children.get(node, []):
            child_take, child_skip = dfs(child)
            take += child_skip
            skip += max(child_take, child_skip)
        return take, skip
    take, skip = dfs(root)
    return max(take, skip)
"""


TREE_MAX_INDEPENDENT_SET_TRACKER = """
def trace(input_data):
    tree = input_data["tree"]
    weights = {str(node["id"]): int(node.get("value", node.get("weight", 1))) for node in tree["nodes"]}
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {str(v) for _, v in tree["edges"]}
    root = ""
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in targets:
            root = node_id
            break
    tracer = Tracer(input_data, algorithm="树形 DP 最大独立集", pseudocode=["dp_take[u] = weight[u] + sum(dp_skip[child])", "dp_skip[u] = sum(max(dp_take[child], dp_skip[child]))"], policy="full", max_events=180)
    call_stack = []
    dp_take = {}
    dp_skip = {}
    return_values = {}
    tracer.create("tree", state={"tree": tree, "current": root, "call_stack": call_stack[:], "dp_take": dict(dp_take), "dp_skip": dict(dp_skip), "return_values": dict(return_values)}, reason="展示带权树，准备后序树形 DP 子树聚合。", code_line=1)
    def dfs(node):
        call_stack.append(node)
        frame = f"frame:tree_dp({node})"
        tracer.enter(frame, deps=[f"node:{node}"], state={"tree": tree, "current": node, "call_stack": call_stack[:], "dp_take": dict(dp_take), "dp_skip": dict(dp_skip), "return_values": dict(return_values)}, role="current", reason="进入当前节点 frame，先计算所有子节点 DP。", code_line=8)
        take = weights[node]
        skip = 0
        for child in children.get(node, []):
            child_take, child_skip = dfs(child)
            take += child_skip
            skip += max(child_take, child_skip)
        dp_take[node] = take
        dp_skip[node] = skip
        return_values[node] = {"take": take, "skip": skip}
        child_deps = [f"frame:tree_dp({child})" for child in children.get(node, [])] or [f"node:{node}"]
        tracer.set(
            f"dp_take[{node}]",
            value=take,
            deps=child_deps + [f"node:{node}"],
            state={"tree": tree, "current": node, "call_stack": call_stack[:], "dp_take": dict(dp_take), "dp_skip": dict(dp_skip), "return_values": dict(return_values)},
            role="answer" if node == root else "current",
            reason="树形 DP 子树聚合：选择当前节点时只能累加子节点不选状态。",
            code_line=13,
        )
        tracer.exit(frame, deps=[f"node:{node}"], state={"tree": tree, "current": node, "call_stack": call_stack[:], "dp_take": dict(dp_take), "dp_skip": dict(dp_skip), "return_values": dict(return_values)}, role="current", reason="当前节点返回 take/skip 两个状态给父 frame。", code_line=15)
        call_stack.pop()
        return take, skip
    root_take, root_skip = dfs(root)
    answer = max(root_take, root_skip)
    tracer.mark(f"node:{root}", deps=[f"frame:tree_dp({root})"], state={"tree": tree, "current": root, "call_stack": [], "dp_take": dict(dp_take), "dp_skip": dict(dp_skip), "return_values": dict(return_values), "answer": answer}, role="answer", reason="根节点两个状态取最大值，得到整棵树最大独立集权重。", code_line=16)
    tracer.result(answer)
    return tracer.to_trace()
"""


TREE_MAX_INDEPENDENT_SET_VERIFIER = """
def verify(input_data):
    tree = input_data["tree"]
    weights = {str(node["id"]): int(node.get("value", node.get("weight", 1))) for node in tree["nodes"]}
    children = {}
    for u, v in tree["edges"]:
        children.setdefault(str(u), []).append(str(v))
    targets = {str(v) for _, v in tree["edges"]}
    root = ""
    for node in tree["nodes"]:
        node_id = str(node["id"])
        if node_id not in targets:
            root = node_id
            break
    def dfs(node):
        take = weights[node]
        skip = 0
        for child in children.get(node, []):
            child_take, child_skip = dfs(child)
            take += child_skip
            skip += max(child_take, child_skip)
        return take, skip
    take, skip = dfs(root)
    return max(take, skip)
"""


PERMUTATIONS_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    ans = []
    used = [False] * len(nums)
    path = []
    def dfs():
        if len(path) == len(nums):
            ans.append(path[:])
            return
        for i, x in enumerate(nums):
            if not used[i]:
                used[i] = True
                path.append(x)
                dfs()
                path.pop()
                used[i] = False
    dfs()
    return ans
"""


PERMUTATIONS_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    ans = []
    used = [False] * len(nums)
    path = []
    tree = {"nodes": [{"id": "root", "label": "[]"}], "edges": []}
    contract = {"family": "backtracking", "submode": "permutations", "expected_events": ["choose", "record", "undo"]}
    tracer = Tracer(input_data, algorithm="全排列回溯", pseudocode=["选择未使用数字加入 path", "path 满长时记录答案", "返回时撤销选择"], policy="full", max_events=260)
    call_stack = ["root"]
    return_values = {}
    tracer.create("recursion_tree", state={"nums": nums, "path": [], "used": used[:], "call_stack": call_stack[:], "return_values": dict(return_values), "recursion_tree": {"nodes": tree["nodes"][:], "edges": tree["edges"][:]}, "family_contract": contract}, reason="从空路径开始回溯搜索。", code_line=1)
    def dfs(parent_id):
        frame = f"frame:perm({parent_id})"
        if len(path) == len(nums):
            ans.append(path[:])
            return_values[parent_id] = path[:]
            tracer.mark(
                f"node:{parent_id}",
                deps=[frame],
                state={"nums": nums, "path": path[:], "used": used[:], "call_stack": call_stack[:], "return_values": dict(return_values), "answer": [x[:] for x in ans], "recursion_tree": {"nodes": tree["nodes"][:], "edges": tree["edges"][:]}, "family_contract": contract},
                role="answer",
                reason="路径长度等于 nums 长度，记录一个排列答案。",
                code_line=7,
            )
            return
        for i, x in enumerate(nums):
            if not used[i]:
                used[i] = True
                path.append(x)
                node_id = f"{parent_id}_{i}_{len(tree['nodes'])}"
                tree["nodes"].append({"id": node_id, "label": str(path[:])})
                tree["edges"].append([parent_id, node_id])
                call_stack.append(node_id)
                tracer.enter(
                    f"frame:perm({node_id})",
                    deps=[f"node:{node_id}", f"node:{parent_id}"],
                    state={"nums": nums, "path": path[:], "used": used[:], "call_stack": call_stack[:], "return_values": dict(return_values), "recursion_tree": {"nodes": tree["nodes"][:], "edges": tree["edges"][:]}, "family_contract": contract},
                    role="current",
                    reason="选择一个未使用数字，进入下一层搜索。",
                    code_line=12,
                )
                dfs(node_id)
                path.pop()
                used[i] = False
                call_stack.pop()
                tracer.exit(
                    f"frame:perm({node_id})",
                    deps=[f"node:{node_id}"],
                    state={"nums": nums, "path": path[:], "used": used[:], "call_stack": call_stack[:], "return_values": dict(return_values), "recursion_tree": {"nodes": tree["nodes"][:], "edges": tree["edges"][:]}, "family_contract": contract},
                    role="current",
                    reason="撤销选择，退出当前回溯 frame，回到父节点继续尝试。",
                    code_line=15,
                )
    dfs("root")
    return_values["root"] = len(ans)
    tracer.mark("recursion_tree", state={"nums": nums, "path": [], "used": used[:], "call_stack": [], "return_values": dict(return_values), "answer": [x[:] for x in ans], "recursion_tree": {"nodes": tree["nodes"][:], "edges": tree["edges"][:]}, "family_contract": contract}, role="answer", reason="根 frame 完成所有分支，得到全部排列。", code_line=16)
    tracer.result(ans)
    return tracer.to_trace()
"""


PERMUTATIONS_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    if not nums:
        return [[]]
    result = []
    for i, x in enumerate(nums):
        rest = nums[:i] + nums[i + 1:]
        for tail in verify({"nums": rest}):
            result.append([x] + tail)
    return result
"""


CONVEX_HULL_CODE = """
def solve(input_data):
    points = [tuple(p) for p in input_data["points"]]
    points = sorted(set(points))
    if len(points) <= 1:
        return [list(p) for p in points]
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    return [list(p) for p in hull]
"""


CONVEX_HULL_TRACKER = """
def trace(input_data):
    raw_points = input_data["points"]
    points = sorted(set(tuple(p) for p in raw_points))
    point_ids = {p: str(i) for i, p in enumerate(points)}
    geometry_points = [{"id": point_ids[p], "x": p[0], "y": p[1], "label": str(list(p))} for p in points]
    def ids(chain):
        return [point_ids[x] for x in chain]
    def lists(chain):
        return [list(x) for x in chain]
    def geom(chain, current=None, closed=False, segments=None, sweep_x=None):
        data = {"points": geometry_points, "hull": ids(chain), "closed": closed}
        if current is not None:
            data["sweep_x"] = current[0] if sweep_x is None else sweep_x
        if segments:
            data["segments"] = segments
        return data
    def state(phase, current, lower, upper, chain, segments=None, closed=False):
        data = {
            "geometry": geom(chain, current=current, closed=closed, segments=segments),
            "phase": phase,
            "current": list(current) if current is not None else None,
            "lower": lists(lower),
            "upper": lists(upper),
        }
        return data
    events = [{
        "step": 0,
        "op": "create",
        "targets": [{"id": "geometry"}],
        "state": {"geometry": {"points": geometry_points}, "phase": "sort", "lower": [], "upper": []},
        "reason": "按坐标排序点集，准备 Andrew 单调链扫描。",
        "code_line": 1,
    }]
    if len(points) <= 1:
        return {"schema_version": "semantic-trace-v1", "algorithm": "凸包", "input_data": input_data, "result": [list(p) for p in points], "events": events}
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for p in points:
        events.append({
            "step": len(events),
            "op": "mark",
            "targets": [{"id": f"point:{point_ids[p]}"}],
            "state": state("lower", p, lower, [], lower),
            "role": "current",
            "reason": "扫描当前点，尝试加入下凸壳。",
            "code_line": 8,
        })
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            removed = lower.pop()
            segments = [
                {"from": point_ids[lower[-1]], "to": point_ids[removed], "label": "old"},
                {"from": point_ids[removed], "to": point_ids[p], "label": "turn"},
            ]
            events.append({
                "step": len(events),
                "op": "pop",
                "targets": [{"id": f"point:{point_ids[removed]}"}],
                "deps": [{"id": f"point:{point_ids[lower[-1]]}"}, {"id": f"point:{point_ids[p]}"}],
                "value": list(removed),
                "state": state("lower", p, lower, [], lower, segments=segments),
                "role": "conflict",
                "reason": "下凸壳末尾三点形成非左转，移除中间点。",
                "code_line": 10,
            })
        lower.append(p)
        events.append({
            "step": len(events),
            "op": "push",
            "targets": [{"id": "lower"}],
            "value": list(p),
            "state": state("lower", p, lower, [], lower),
            "role": "current",
            "reason": "加入当前点后，下凸壳保持左转不变量。",
            "code_line": 11,
        })
    upper = []
    for p in reversed(points):
        events.append({
            "step": len(events),
            "op": "mark",
            "targets": [{"id": f"point:{point_ids[p]}"}],
            "state": state("upper", p, lower, upper, upper),
            "role": "current",
            "reason": "反向扫描当前点，尝试加入上凸壳。",
            "code_line": 14,
        })
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            removed = upper.pop()
            segments = [
                {"from": point_ids[upper[-1]], "to": point_ids[removed], "label": "old"},
                {"from": point_ids[removed], "to": point_ids[p], "label": "turn"},
            ]
            events.append({
                "step": len(events),
                "op": "pop",
                "targets": [{"id": f"point:{point_ids[removed]}"}],
                "deps": [{"id": f"point:{point_ids[upper[-1]]}"}, {"id": f"point:{point_ids[p]}"}],
                "value": list(removed),
                "state": state("upper", p, lower, upper, upper, segments=segments),
                "role": "conflict",
                "reason": "上凸壳末尾三点形成非左转，移除中间点。",
                "code_line": 16,
            })
        upper.append(p)
        events.append({
            "step": len(events),
            "op": "push",
            "targets": [{"id": "upper"}],
            "value": list(p),
            "state": state("upper", p, lower, upper, upper),
            "role": "current",
            "reason": "加入当前点后，上凸壳保持左转不变量。",
            "code_line": 17,
        })
    hull = lower[:-1] + upper[:-1]
    result = [list(p) for p in hull]
    final_state = state("final", None, lower, upper, hull, closed=True)
    final_state["answer"] = result
    events.append({
        "step": len(events),
        "op": "mark",
        "targets": [{"id": "geometry"}],
        "state": final_state,
        "role": "answer",
        "reason": "合并上下凸壳并闭合，得到最终凸包。",
        "code_line": 19,
    })
    return {"schema_version": "semantic-trace-v1", "algorithm": "凸包", "input_data": input_data, "result": result, "pseudocode": ["排序点集", "维护下凸壳和上凸壳", "合并得到凸包"], "events": events}
"""


CONVEX_HULL_VERIFIER = """
def verify(input_data):
    points = [tuple(p) for p in input_data["points"]]
    points = sorted(set(points))
    if len(points) <= 1:
        return [list(p) for p in points]
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return [list(p) for p in lower[:-1] + upper[:-1]]
"""


SEGMENT_TREE_RANGE_SUM_CODE = """
def solve(input_data):
    nums = input_data["nums"][:]
    query = input_data["query"]
    update = input_data["update"]
    left, right = query[0], query[1]
    before = sum(nums[left:right + 1])
    nums[update[0]] = update[1]
    after = sum(nums[left:right + 1])
    return {"before": before, "after": after}
"""


SEGMENT_TREE_RANGE_SUM_TRACKER = """
def trace(input_data):
    nums = input_data["nums"][:]
    query = input_data["query"][:]
    update = input_data["update"][:]
    tracer = Tracer(
        input_data,
        algorithm="线段树区间和",
        pseudocode=["build(node,l,r)", "query(node,l,r,ql,qr)", "update(node,l,r,pos,value)"],
        policy="full",
        max_events=220,
    )

    def build_tree(values):
        nodes = []
        edges = []
        sums = {}
        if not values:
            return {"nodes": nodes, "edges": edges}, sums

        def build(idx, left, right):
            node_id = f"seg_{idx}_{left}_{right}"
            if left == right:
                total = values[left]
            else:
                mid = (left + right) // 2
                left_id, left_sum = build(idx * 2, left, mid)
                right_id, right_sum = build(idx * 2 + 1, mid + 1, right)
                edges.append([node_id, left_id])
                edges.append([node_id, right_id])
                total = left_sum + right_sum
            sums[node_id] = total
            nodes.append({"id": node_id, "label": f"[{left},{right}]={total}", "meta": {"l": left, "r": right, "sum": total}})
            return node_id, total

        build(1, 0, len(values) - 1)
        return {"nodes": nodes, "edges": edges}, sums

    def state(answer=None):
        segment_tree, _sums = build_tree(nums)
        data = {"nums": nums[:], "query": query[:], "update": update[:], "segment_tree": segment_tree}
        if answer is not None:
            data["answer"] = answer
        return data

    tracer.create(
        "segment_tree",
        state=state(),
        reason="用线段树节点 label/meta 表示每个节点覆盖区间和，不使用 range: target。",
        code_line=1,
    )

    def query_range(idx, left, right, ql, qr, covered, answer):
        node_id = f"seg_{idx}_{left}_{right}"
        segment_tree, sums = build_tree(nums)
        current_state = {"nums": nums[:], "query": query[:], "update": update[:], "segment_tree": segment_tree}
        if answer is not None:
            current_state["answer"] = answer
        if qr < left or right < ql:
            tracer.compare(
                [f"node:{node_id}"],
                deps=["query[0]", "query[1]"],
                state=current_state,
                role="candidate",
                reason="查询区间与当前线段树节点无交集，查询路径跳过该节点。",
                code_line=6,
            )
            return 0
        if ql <= left and right <= qr:
            covered.append(f"node:{node_id}")
            tracer.mark(
                f"node:{node_id}",
                value=sums[node_id],
                deps=["query[0]", "query[1]"],
                state=current_state,
                role="current",
                reason="查询区间完全覆盖该线段树节点，直接使用 node meta 中的区间和。",
                code_line=7,
            )
            return sums[node_id]
        tracer.compare(
            [f"node:{node_id}"],
            deps=["query[0]", "query[1]"],
            state=current_state,
            role="candidate",
            reason="查询区间与当前节点部分重叠，查询路径继续访问左右子树。",
            code_line=8,
        )
        mid = (left + right) // 2
        return query_range(idx * 2, left, mid, ql, qr, covered, answer) + query_range(idx * 2 + 1, mid + 1, right, ql, qr, covered, answer)

    left, right = query[0], query[1]
    covered_before = []
    before = query_range(1, 0, len(nums) - 1, left, right, covered_before, None)
    tracer.set(
        "answer",
        value={"before": before},
        deps=covered_before,
        state=state({"before": before}),
        role="current",
        reason="查询区间由这些覆盖节点相加得到更新前答案。",
        code_line=10,
    )

    pos, new_value = update[0], update[1]
    old_value = nums[pos]

    def update_point(idx, left, right):
        node_id = f"seg_{idx}_{left}_{right}"
        if left == right:
            nums[pos] = new_value
            tracer.set(
                f"nums[{pos}]",
                before=old_value,
                after=new_value,
                deps=["update[0]", "update[1]", f"node:{node_id}"],
                state=state({"before": before}),
                role="current",
                reason="更新路径到达叶子，把 update 指定的新值写回原数组。",
                code_line=13,
            )
            segment_tree, sums = build_tree(nums)
            tracer.set(
                f"node:{node_id}",
                value=sums[node_id],
                deps=[f"nums[{pos}]"],
                state={"nums": nums[:], "query": query[:], "update": update[:], "segment_tree": segment_tree, "answer": {"before": before}},
                role="current",
                reason="更新路径上的叶子线段树节点同步新的单点值。",
                code_line=14,
            )
            return
        mid = (left + right) // 2
        if pos <= mid:
            update_point(idx * 2, left, mid)
            child_id = f"seg_{idx * 2}_{left}_{mid}"
        else:
            update_point(idx * 2 + 1, mid + 1, right)
            child_id = f"seg_{idx * 2 + 1}_{mid + 1}_{right}"
        segment_tree, sums = build_tree(nums)
        tracer.set(
            f"node:{node_id}",
            value=sums[node_id],
            deps=[f"node:{child_id}"],
            state={"nums": nums[:], "query": query[:], "update": update[:], "segment_tree": segment_tree, "answer": {"before": before}},
            role="current",
            reason="更新路径回溯，重新计算当前线段树节点的区间和。",
            code_line=16,
        )

    update_point(1, 0, len(nums) - 1)
    covered_after = []
    after = query_range(1, 0, len(nums) - 1, left, right, covered_after, {"before": before})
    result = {"before": before, "after": after}
    tracer.set(
        "answer",
        value=result,
        deps=covered_after,
        state=state(result),
        role="answer",
        reason="更新后再次执行查询区间覆盖节点求和，得到最终答案。",
        code_line=18,
    )
    tracer.result(result)
    return tracer.to_trace()
"""


SEGMENT_TREE_RANGE_SUM_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"][:]
    left, right = input_data["query"]
    before = sum(nums[left:right + 1])
    pos, value = input_data["update"]
    nums[pos] = value
    after = sum(nums[left:right + 1])
    return {"before": before, "after": after}
"""


FENWICK_TREE_PREFIX_SUM_CODE = """
def solve(input_data):
    nums = input_data["nums"][:]
    left, right = input_data["query"]
    pos, delta = input_data["update"]
    before = sum(nums[left:right + 1])
    nums[pos] += delta
    after = sum(nums[left:right + 1])
    return {"before": before, "after": after}
"""


FENWICK_TREE_PREFIX_SUM_TRACKER = """
def trace(input_data):
    nums = input_data["nums"][:]
    query = input_data["query"][:]
    update = input_data["update"][:]

    def build_bit(values):
        bit = [0] * (len(values) + 1)
        for i, value in enumerate(values):
            j = i + 1
            while j <= len(values):
                bit[j] += value
                j += j & -j
        return bit

    bit = build_bit(nums)
    tracer = Tracer(
        input_data,
        algorithm="树状数组前缀和",
        pseudocode=["bit[i] 覆盖 i-lowbit(i)+1 到 i", "prefix(x) 沿 lowbit 向前累加", "add(pos,delta) 沿 lowbit 向后更新"],
        policy="full",
        max_events=180,
    )

    def state(answer=None):
        data = {"nums": nums[:], "bit": bit[:], "query": query[:], "update": update[:]}
        if answer is not None:
            data["answer"] = answer
        return data

    tracer.create(
        "bit",
        state=state(),
        reason="初始化树状数组 bit；bit[i] 维护一个 lowbit 长度的前缀块。",
        code_line=1,
    )

    def prefix_sum(pos, label, answer=None):
        total = 0
        deps = []
        j = pos
        while j > 0:
            total += bit[j]
            deps.append(f"bit[{j}]")
            tracer.mark(
                f"bit[{j}]",
                value=total,
                deps=["query[0]", "query[1]"],
                state=state(answer),
                role="current",
                reason=f"{label} 前缀和查询沿 lowbit 路径累加 bit[{j}]。",
                code_line=7,
            )
            j -= j & -j
        return total, deps

    left, right = query[0], query[1]
    right_sum, right_deps = prefix_sum(right + 1, "右端", None)
    left_sum, left_deps = prefix_sum(left, "左端前一位", None)
    before = right_sum - left_sum
    tracer.set(
        "answer",
        value={"before": before},
        deps=right_deps + left_deps,
        state=state({"before": before}),
        role="current",
        reason="区间和等于右端前缀减去左端前一位前缀。",
        code_line=9,
    )

    pos, delta = update[0], update[1]
    old_nums = nums[:]
    old_bit = bit[:]
    path = []
    j = pos + 1
    while j <= len(nums):
        path.append(j)
        j += j & -j
    nums[pos] += delta
    bit = build_bit(nums)
    tracer.set(
        f"nums[{pos}]",
        before=old_nums[pos],
        after=nums[pos],
        deps=["update[0]", "update[1]"],
        state=state({"before": before}),
        role="current",
        reason="把 update 的增量写入原数组，随后沿树状数组更新路径同步。",
        code_line=12,
    )
    for index in path:
        tracer.set(
            f"bit[{index}]",
            before=old_bit[index],
            after=bit[index],
            value=bit[index],
            deps=[f"nums[{pos}]", "update[0]", "update[1]"],
            state=state({"before": before}),
            role="current",
            reason=f"更新路径沿 lowbit 向后跳到 bit[{index}]，维护它覆盖的前缀块。",
            code_line=14,
        )

    right_sum_after, right_deps_after = prefix_sum(right + 1, "更新后右端", {"before": before})
    left_sum_after, left_deps_after = prefix_sum(left, "更新后左端前一位", {"before": before})
    after = right_sum_after - left_sum_after
    result = {"before": before, "after": after}
    tracer.set(
        "answer",
        value=result,
        deps=right_deps_after + left_deps_after,
        state=state(result),
        role="answer",
        reason="更新后再次计算两个前缀和之差，得到最终区间和。",
        code_line=16,
    )
    tracer.result(result)
    return tracer.to_trace()
"""


FENWICK_TREE_PREFIX_SUM_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"][:]
    left, right = input_data["query"]
    pos, delta = input_data["update"]
    before = sum(nums[left:right + 1])
    nums[pos] += delta
    after = sum(nums[left:right + 1])
    return {"before": before, "after": after}
"""


SPARSE_TABLE_RANGE_MIN_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    left, right = input_data["query"]
    answer = nums[left]
    for i in range(left, right + 1):
        if nums[i] < answer:
            answer = nums[i]
    return answer
"""


SPARSE_TABLE_RANGE_MIN_TRACKER = """
def trace(input_data):
    nums = input_data["nums"][:]
    query = input_data["query"][:]

    def build_sparse(values):
        n = len(values)
        log = [0] * (n + 1)
        for i in range(2, n + 1):
            log[i] = log[i // 2] + 1
        levels = log[n] + 1 if n else 1
        st = [[None] * n for _ in range(levels)]
        for i, value in enumerate(values):
            st[0][i] = value
        k = 1
        while (1 << k) <= n:
            half = 1 << (k - 1)
            span = 1 << k
            for i in range(0, n - span + 1):
                left_value = st[k - 1][i]
                right_value = st[k - 1][i + half]
                st[k][i] = min(left_value, right_value)
            k += 1
        return st, log

    st, log = build_sparse(nums)
    tracer = Tracer(
        input_data,
        algorithm="稀疏表区间最小值",
        pseudocode=["st[k][i] = min(st[k-1][i], st[k-1][i+2^(k-1)])", "query 用两个长度 2^k 的重叠区间"],
        policy="full",
        max_events=180,
    )

    def state(answer=None):
        data = {"nums": nums[:], "st": [row[:] for row in st], "log": log[:], "query": query[:]}
        if answer is not None:
            data["answer"] = answer
        return data

    tracer.create(
        "st",
        state=state(),
        reason="初始化稀疏表第一层，后续每层表示固定长度区间的最小值。",
        code_line=1,
    )
    for k in range(1, len(st)):
        half = 1 << (k - 1)
        span = 1 << k
        for i in range(0, len(nums) - span + 1):
            tracer.set(
                f"st[{k}][{i}]",
                value=st[k][i],
                deps=[f"st[{k - 1}][{i}]", f"st[{k - 1}][{i + half}]"],
                state=state(),
                role="current",
                reason="稀疏表用两个相邻半区间的最小值合成更长区间。",
                code_line=8,
            )

    left, right = query[0], query[1]
    length = right - left + 1
    k = log[length]
    right_start = right - (1 << k) + 1
    answer = min(st[k][left], st[k][right_start])
    tracer.compare(
        [f"st[{k}][{left}]", f"st[{k}][{right_start}]"],
        deps=["query[0]", "query[1]"],
        state=state(),
        role="candidate",
        reason="稀疏表查询用两个可重叠区间覆盖原查询区间。",
        code_line=12,
    )
    tracer.set(
        "answer",
        value=answer,
        deps=[f"st[{k}][{left}]", f"st[{k}][{right_start}]"],
        state=state(answer),
        role="answer",
        reason="两个重叠区间的最小值取 min，就是查询区间答案。",
        code_line=13,
    )
    tracer.result(answer)
    return tracer.to_trace()
"""


SPARSE_TABLE_RANGE_MIN_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    left, right = input_data["query"]
    answer = nums[left]
    for i in range(left, right + 1):
        if nums[i] < answer:
            answer = nums[i]
    return answer
"""


GCD_EUCLID_CODE = """
def solve(input_data):
    a = abs(input_data["a"])
    b = abs(input_data["b"])
    while b:
        a, b = b, a % b
    return a
"""


GCD_EUCLID_TRACKER = """
def trace(input_data):
    original_a = abs(input_data["a"])
    original_b = abs(input_data["b"])
    a = original_a
    b = original_b
    tracer = Tracer(
        input_data,
        algorithm="最大公约数 Euclid",
        pseudocode=["gcd(a,b) = gcd(b, a % b)", "余数为 0 时当前 b 是最大公约数"],
        policy="full",
        max_events=120,
    )
    remainders = []
    tracer.create(
        "remainders",
        state={"a": a, "b": b, "remainders": remainders[:]},
        reason="初始化 Euclid 最大公约数过程，保持 gcd(a,b) 不变量。",
        code_line=1,
    )
    if b == 0:
        tracer.set(
            "answer",
            value=a,
            deps=["a"],
            state={"a": a, "b": b, "remainders": remainders[:], "answer": a},
            role="answer",
            reason="b 为 0，最大公约数就是当前 a。",
            code_line=2,
        )
        tracer.result(a)
        return tracer.to_trace()
    while b:
        r = a % b
        remainders.append(r)
        tracer.set(
            f"remainders[{len(remainders) - 1}]",
            value=r,
            deps=["a", "b"],
            state={"a": a, "b": b, "remainders": remainders[:]},
            role="current",
            reason="Euclid 不变量：gcd(a,b) 等于 gcd(b,a mod b)，记录本轮余数。",
            code_line=4,
        )
        a, b = b, r
    tracer.set(
        "answer",
        value=a,
        deps=[f"remainders[{len(remainders) - 1}]"] if remainders else ["a"],
        state={"a": a, "b": b, "remainders": remainders[:], "answer": a},
        role="answer",
        reason="余数为 0 时，当前 a 是最大公约数。",
        code_line=5,
    )
    tracer.result(a)
    return tracer.to_trace()
"""


GCD_EUCLID_VERIFIER = """
def verify(input_data):
    a = abs(input_data["a"])
    b = abs(input_data["b"])
    while b:
        a, b = b, a % b
    return a
"""


FAST_POWER_MOD_CODE = """
def solve(input_data):
    base = input_data["base"]
    exponent = input_data["exponent"]
    mod = input_data["mod"]
    result = 1 % mod
    cur = base % mod
    e = exponent
    while e:
        if e & 1:
            result = (result * cur) % mod
        cur = (cur * cur) % mod
        e >>= 1
    return result
"""


FAST_POWER_MOD_TRACKER = """
def trace(input_data):
    base = input_data["base"]
    exponent = input_data["exponent"]
    mod = input_data["mod"]
    bits = []
    e = exponent
    if e == 0:
        bits = [0]
    while e:
        bits.append(e & 1)
        e >>= 1
    tracer = Tracer(
        input_data,
        algorithm="快速幂取模",
        pseudocode=["按指数二进制位扫描", "powers[i] = base^(2^i) mod mod", "当前位为 1 时乘入答案"],
        policy="full",
        max_events=160,
    )
    powers = []
    answer = 1 % mod
    tracer.create(
        "bits",
        state={"base": base, "exponent": exponent, "mod": mod, "bits": bits[:], "powers": powers[:], "answer": answer},
        reason="把指数拆成二进制 bits，准备快速幂平方表。",
        code_line=1,
    )
    cur = base % mod
    for i, bit in enumerate(bits):
        powers.append(cur)
        tracer.set(
            f"powers[{i}]",
            value=cur,
            deps=["base", "mod"] if i == 0 else [f"powers[{i - 1}]", "mod"],
            state={"base": base, "exponent": exponent, "mod": mod, "bits": bits[:], "powers": powers[:], "answer": answer},
            role="current",
            reason="快速幂不变量：powers[i] 表示 base 的 2^i 次方取模。",
            code_line=6,
        )
        if bit:
            answer = (answer * cur) % mod
            tracer.set(
                "answer",
                value=answer,
                deps=[f"powers[{i}]", f"bits[{i}]"],
                state={"base": base, "exponent": exponent, "mod": mod, "bits": bits[:], "powers": powers[:], "answer": answer},
                role="current",
                reason="指数当前二进制位为 1，把对应幂乘入答案。",
                code_line=8,
            )
        cur = (cur * cur) % mod
    tracer.set(
        "answer",
        value=answer,
        deps=[f"powers[{i}]" for i, bit in enumerate(bits) if bit],
        state={"base": base, "exponent": exponent, "mod": mod, "bits": bits[:], "powers": powers[:], "answer": answer},
        role="answer",
        reason="所有指数位处理完毕，得到快速幂取模结果。",
        code_line=10,
    )
    tracer.result(answer)
    return tracer.to_trace()
"""


FAST_POWER_MOD_VERIFIER = """
def verify(input_data):
    return pow(input_data["base"], input_data["exponent"], input_data["mod"])
"""


SIEVE_PRIMES_CODE = """
def solve(input_data):
    n = input_data["n"]
    if n < 2:
        return []
    is_prime = [True] * (n + 1)
    is_prime[0] = False
    is_prime[1] = False
    p = 2
    while p * p <= n:
        if is_prime[p]:
            m = p * p
            while m <= n:
                is_prime[m] = False
                m += p
        p += 1
    return [i for i in range(2, n + 1) if is_prime[i]]
"""


SIEVE_PRIMES_TRACKER = """
def trace(input_data):
    n = input_data["n"]
    is_prime = [True] * (n + 1)
    if n >= 0:
        is_prime[0] = False
    if n >= 1:
        is_prime[1] = False
    tracer = Tracer(
        input_data,
        algorithm="埃氏筛",
        pseudocode=["从 2 开始枚举质数候选", "把每个质数的倍数标记为合数"],
        policy="full",
        max_events=240,
    )
    tracer.create(
        "is_prime",
        state={"n": n, "is_prime": is_prime[:], "current": None, "multiples": [], "answer": []},
        reason="初始化筛法布尔数组，0 和 1 不是质数。",
        code_line=1,
    )
    p = 2
    while p * p <= n:
        multiples = []
        if is_prime[p]:
            m = p * p
            while m <= n:
                if is_prime[m]:
                    is_prime[m] = False
                    multiples.append(m)
                    tracer.set(
                        f"is_prime[{m}]",
                        value=False,
                        deps=[f"is_prime[{p}]"],
                        state={"n": n, "is_prime": is_prime[:], "current": p, "multiples": multiples[:], "answer": []},
                        role="current",
                        reason="筛法不变量：当前质数的倍数一定不是质数，标记为合数。",
                        code_line=8,
                    )
                m += p
        p += 1
    answer = [i for i in range(2, n + 1) if is_prime[i]]
    tracer.set(
        "answer",
        value=answer,
        deps=[f"is_prime[{i}]" for i in answer],
        state={"n": n, "is_prime": is_prime[:], "current": p - 1, "multiples": [], "answer": answer},
        role="answer",
        reason="筛法结束，仍为 True 的下标就是质数。",
        code_line=12,
    )
    tracer.result(answer)
    return tracer.to_trace()
"""


SIEVE_PRIMES_VERIFIER = """
def verify(input_data):
    n = input_data["n"]
    result = []
    for x in range(2, n + 1):
        ok = True
        d = 2
        while d * d <= x:
            if x % d == 0:
                ok = False
                break
            d += 1
        if ok:
            result.append(x)
    return result
"""


COMBINATIONS_PASCAL_CODE = """
def solve(input_data):
    n = input_data["n"]
    k = input_data["k"]
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    table = [[0] * (k + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        table[i][0] = 1
        upper = min(i, k)
        for j in range(1, upper + 1):
            if j == i:
                table[i][j] = 1
            else:
                table[i][j] = table[i - 1][j - 1] + table[i - 1][j]
    return table[n][k]
"""


COMBINATIONS_PASCAL_TRACKER = """
def trace(input_data):
    n = input_data["n"]
    k = input_data["k"]
    width = k + 1
    table = [[0] * width for _ in range(n + 1)]
    tracer = Tracer(
        input_data,
        algorithm="组合数 Pascal",
        pseudocode=["C(i,0)=1", "C(i,j)=C(i-1,j-1)+C(i-1,j)"],
        policy="full",
        max_events=240,
    )
    tracer.create(
        "table",
        state={"n": n, "k": k, "table": [row[:] for row in table]},
        reason="初始化组合数 DP 表，使用帕斯卡恒等式填表。",
        code_line=1,
    )
    for i in range(n + 1):
        table[i][0] = 1
        tracer.set(
            f"table[{i}][0]",
            value=1,
            deps=[],
            state={"n": n, "k": k, "table": [row[:] for row in table]},
            role="current",
            reason="组合数边界：C(i,0)=1。",
            code_line=3,
        )
        upper = min(i, k)
        for j in range(1, upper + 1):
            if j == i:
                table[i][j] = 1
                deps = []
                reason = "组合数边界：C(i,i)=1。"
            else:
                table[i][j] = table[i - 1][j - 1] + table[i - 1][j]
                deps = [f"table[{i - 1}][{j - 1}]", f"table[{i - 1}][{j}]"]
                reason = "帕斯卡恒等式：组合数来自左上和正上两个状态之和。"
            tracer.set(
                f"table[{i}][{j}]",
                value=table[i][j],
                deps=deps,
                state={"n": n, "k": k, "table": [row[:] for row in table]},
                role="current",
                reason=reason,
                code_line=6,
            )
    answer = table[n][k] if 0 <= k <= n else 0
    tracer.set(
        "answer",
        value=answer,
        deps=[f"table[{n}][{k}]"] if 0 <= k <= n else [],
        state={"n": n, "k": k, "table": [row[:] for row in table], "answer": answer},
        role="answer",
        reason="目标格就是所求组合数。",
        code_line=9,
    )
    tracer.result(answer)
    return tracer.to_trace()
"""


COMBINATIONS_PASCAL_VERIFIER = """
def verify(input_data):
    n = input_data["n"]
    k = input_data["k"]
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    result = 1
    for i in range(1, k + 1):
        result = result * (n - k + i) // i
    return result
"""


BITMASK_SUBSETS_CODE = """
def solve(input_data):
    nums = input_data["nums"]
    result = []
    for mask in range(1 << len(nums)):
        subset = []
        for i, value in enumerate(nums):
            if (mask >> i) & 1:
                subset.append(value)
        result.append(subset)
    return result
"""


BITMASK_SUBSETS_TRACKER = """
def trace(input_data):
    nums = input_data["nums"]
    n = len(nums)
    tracer = Tracer(
        input_data,
        algorithm="位掩码枚举子集",
        pseudocode=["mask 的第 i 位表示是否选择 nums[i]", "枚举 0 到 2^n-1 得到所有子集"],
        policy="full",
        max_events=260,
    )
    answer = []
    bits = [0] * n
    tracer.create(
        "bits",
        state={"nums": nums, "mask": 0, "bits": bits[:], "subset": [], "answer": []},
        reason="初始化位掩码枚举，bits 展示 mask 的每一位。",
        code_line=1,
    )
    for mask in range(1 << n):
        bits = [((mask >> i) & 1) for i in range(n)]
        subset = []
        for i, bit in enumerate(bits):
            if bit:
                subset.append(nums[i])
            tracer.set(
                f"bits[{i}]",
                value=bit,
                deps=["mask", f"nums[{i}]"],
                state={"nums": nums, "mask": mask, "bits": bits[:], "subset": subset[:], "answer": [item[:] for item in answer]},
                role="current",
                reason="位掩码第 i 位决定当前子集是否选择 nums[i]。",
                code_line=5,
            )
        answer.append(subset[:])
        tracer.set(
            "answer",
            value=[item[:] for item in answer],
            deps=[f"bits[{i}]" for i in range(n)],
            state={"nums": nums, "mask": mask, "bits": bits[:], "subset": subset[:], "answer": [item[:] for item in answer]},
            role="current",
            reason="当前 mask 对应的子集已生成并加入答案。",
            code_line=7,
        )
    tracer.result(answer)
    return tracer.to_trace()
"""


BITMASK_SUBSETS_VERIFIER = """
def verify(input_data):
    nums = input_data["nums"]
    result = []
    for mask in range(1 << len(nums)):
        subset = []
        for i, value in enumerate(nums):
            if (mask >> i) & 1:
                subset.append(value)
        result.append(subset)
    return result
"""


LOWBIT_DECOMPOSITION_CODE = """
def solve(input_data):
    remaining = input_data["n"]
    result = []
    while remaining:
        low = remaining & -remaining
        result.append(low)
        remaining -= low
    return result
"""


LOWBIT_DECOMPOSITION_TRACKER = """
def trace(input_data):
    n = input_data["n"]
    bits = []
    value = n
    if value == 0:
        bits = [0]
    while value:
        bits.append(value & 1)
        value >>= 1
    tracer = Tracer(
        input_data,
        algorithm="lowbit 分解",
        pseudocode=["lowbit(x)=x & -x", "每次删除最低位的 1"],
        policy="full",
        max_events=120,
    )
    remaining = n
    lowbits = []
    tracer.create(
        "bits",
        state={"n": n, "remaining": remaining, "bits": bits[:], "lowbits": lowbits[:]},
        reason="展示 n 的二进制位，准备逐次取最低位的 1。",
        code_line=1,
    )
    while remaining:
        low = remaining & -remaining
        lowbits.append(low)
        tracer.set(
            f"lowbits[{len(lowbits) - 1}]",
            value=low,
            deps=["remaining"],
            state={"n": n, "remaining": remaining, "bits": bits[:], "lowbit": low, "lowbits": lowbits[:]},
            role="current",
            reason="lowbit 取出 remaining 的最低位 1 所代表的值。",
            code_line=3,
        )
        remaining -= low
        tracer.set(
            "remaining",
            value=remaining,
            deps=[f"lowbits[{len(lowbits) - 1}]"],
            state={"n": n, "remaining": remaining, "bits": bits[:], "lowbits": lowbits[:]},
            role="current",
            reason="删除最低位的 1，继续分解剩余部分。",
            code_line=4,
        )
    tracer.set(
        "answer",
        value=lowbits[:],
        deps=[f"lowbits[{i}]" for i in range(len(lowbits))],
        state={"n": n, "remaining": remaining, "bits": bits[:], "lowbits": lowbits[:], "answer": lowbits[:]},
        role="answer",
        reason="所有 lowbit 项相加等于原始 n。",
        code_line=5,
    )
    tracer.result(lowbits)
    return tracer.to_trace()
"""


LOWBIT_DECOMPOSITION_VERIFIER = """
def verify(input_data):
    remaining = input_data["n"]
    result = []
    while remaining:
        low = remaining & -remaining
        result.append(low)
        remaining -= low
    return result
"""


TARJAN_SCC_CODE = """
def solve(input_data):
    graph = input_data["graph"]
    index = 0
    dfn = {}
    low = {}
    stack = []
    on_stack = set()
    components = []

    def dfs(u):
        nonlocal index
        index += 1
        dfn[u] = low[u] = index
        stack.append(u)
        on_stack.add(u)
        for v in graph.get(u, []):
            if v not in dfn:
                dfs(v)
                low[u] = min(low[u], low[v])
            elif v in on_stack:
                low[u] = min(low[u], dfn[v])
        if low[u] == dfn[u]:
            component = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.append(w)
                if w == u:
                    break
            components.append(component)

    for node in graph:
        if node not in dfn:
            dfs(node)
    return components
"""


TARJAN_SCC_TRACKER = """
def trace(input_data):
    graph = input_data["graph"]
    tracer = Tracer(
        input_data,
        algorithm="Tarjan 强连通分量",
        pseudocode=[
            "dfn[u] 记录 DFS 访问次序",
            "low[u] 记录 u 能回到的最早 dfn",
            "low[u] == dfn[u] 时弹出一个 SCC",
        ],
    )
    index = 0
    dfn = {}
    low = {}
    stack = []
    on_stack = {}
    components = []

    def snapshot(component=None):
        return {
            "graph": graph,
            "dfn": dict(dfn),
            "low": dict(low),
            "stack": stack[:],
            "on_stack": dict(on_stack),
            "component": list(component or []),
        }

    tracer.create("graph", state=snapshot(), reason="初始化 Tarjan 所需的 dfn、low 和 stack。", code_line=1)

    def dfs(u):
        nonlocal index
        index += 1
        dfn[u] = low[u] = index
        stack.append(u)
        on_stack[u] = True
        tracer.set(
            f"dfn[{u}]",
            value=index,
            deps=[f"node:{u}"],
            state=snapshot(),
            role="current",
            reason="Tarjan 首次访问节点，写入 dfn 并把节点压入 stack。",
            code_line=2,
        )
        tracer.set(
            f"low[{u}]",
            value=index,
            deps=[f"dfn[{u}]"],
            state=snapshot(),
            role="current",
            reason="Tarjan 初始化 low[u] = dfn[u]。",
            code_line=2,
        )
        for v in graph.get(u, []):
            tracer.compare(
                [f"edge:{u}->{v}"],
                deps=[f"node:{u}", f"node:{v}"],
                state=snapshot(),
                role="candidate",
                reason="检查有向边，决定是否 DFS 或用栈内祖先更新 low。",
                code_line=3,
            )
            if v not in dfn:
                dfs(v)
                if low[v] < low[u]:
                    low[u] = low[v]
                    tracer.set(
                        f"low[{u}]",
                        value=low[u],
                        deps=[f"low[{v}]", f"edge:{u}->{v}"],
                        state=snapshot(),
                        role="current",
                        reason="Tarjan 子节点返回后，用 low[v] 更新 low[u]。",
                        code_line=5,
                    )
            elif on_stack.get(v):
                if dfn[v] < low[u]:
                    low[u] = dfn[v]
                    tracer.set(
                        f"low[{u}]",
                        value=low[u],
                        deps=[f"dfn[{v}]", f"edge:{u}->{v}"],
                        state=snapshot(),
                        role="current",
                        reason="Tarjan 遇到栈内回边，用 dfn[v] 更新 low[u]。",
                        code_line=7,
                    )
        if low[u] == dfn[u]:
            component = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                component.append(w)
                if w == u:
                    break
            components.append(component[:])
            tracer.mark(
                f"node:{u}",
                deps=[f"low[{u}]", f"dfn[{u}]"],
                state=snapshot(component),
                role="component",
                reason="Tarjan 发现 low[u] == dfn[u]，从 stack 弹出一个强连通分量。",
                code_line=8,
            )

    for node in graph:
        if node not in dfn:
            dfs(node)
    tracer.result(components)
    return tracer.to_trace()
"""


TARJAN_SCC_VERIFIER = TARJAN_SCC_CODE.replace("def solve(input_data):", "def verify(input_data):")


ARTICULATION_BRIDGES_CODE = """
def solve(input_data):
    graph = input_data["graph"]
    timer = 0
    dfn = {}
    low = {}
    parent = {}
    articulation = set()
    bridges = []

    def dfs(u, root):
        nonlocal timer
        timer += 1
        dfn[u] = low[u] = timer
        child_count = 0
        for v in graph.get(u, []):
            if v == parent.get(u):
                continue
            if v not in dfn:
                parent[v] = u
                child_count += 1
                dfs(v, root)
                low[u] = min(low[u], low[v])
                if low[v] > dfn[u]:
                    bridges.append([u, v])
                if u != root and low[v] >= dfn[u]:
                    articulation.add(u)
            else:
                low[u] = min(low[u], dfn[v])
        if u == root and child_count > 1:
            articulation.add(u)

    for node in graph:
        if node not in dfn:
            parent[node] = None
            dfs(node, node)
    return {"articulation": sorted(articulation), "bridges": bridges}
"""


ARTICULATION_BRIDGES_TRACKER = """
def trace(input_data):
    graph = input_data["graph"]
    tracer = Tracer(
        input_data,
        algorithm="割点和桥 Tarjan",
        pseudocode=[
            "low[child] > dfn[u] 时 (u, child) 是桥",
            "非根节点存在 child 使 low[child] >= dfn[u] 时 u 是割点",
        ],
    )
    timer = 0
    dfn = {}
    low = {}
    parent = {}
    articulation = set()
    bridges = []

    def snapshot():
        return {
            "graph": graph,
            "dfn": dict(dfn),
            "low": dict(low),
            "parent": dict(parent),
            "bridges": [edge[:] for edge in bridges],
            "articulation": sorted(articulation),
        }

    tracer.create("graph", state=snapshot(), reason="初始化割点和桥的 dfn、low、parent。", code_line=1)

    def dfs(u, root):
        nonlocal timer
        timer += 1
        dfn[u] = low[u] = timer
        tracer.set(
            f"dfn[{u}]",
            value=timer,
            deps=[f"node:{u}"],
            state=snapshot(),
            role="current",
            reason="Tarjan 访问节点，写入 dfn 和 low 初值。",
            code_line=2,
        )
        tracer.set(
            f"low[{u}]",
            value=timer,
            deps=[f"dfn[{u}]"],
            state=snapshot(),
            role="current",
            reason="low 初始等于 dfn。",
            code_line=2,
        )
        child_count = 0
        for v in graph.get(u, []):
            if v == parent.get(u):
                continue
            tracer.compare(
                [f"edge:{u}->{v}"],
                deps=[f"node:{u}", f"node:{v}"],
                state=snapshot(),
                role="candidate",
                reason="检查 DFS 树边或返祖边，用于判定桥和割点。",
                code_line=3,
            )
            if v not in dfn:
                parent[v] = u
                child_count += 1
                dfs(v, root)
                if low[v] < low[u]:
                    low[u] = low[v]
                    tracer.set(
                        f"low[{u}]",
                        value=low[u],
                        deps=[f"low[{v}]", f"edge:{u}->{v}"],
                        state=snapshot(),
                        role="current",
                        reason="子树返回后用 low[child] 更新 low[u]。",
                        code_line=5,
                    )
                if low[v] > dfn[u]:
                    bridges.append([u, v])
                    tracer.mark(
                        f"edge:{u}->{v}",
                        deps=[f"low[{v}]", f"dfn[{u}]"],
                        state=snapshot(),
                        role="bridge",
                        reason="low[child] > dfn[u]，这条边是桥。",
                        code_line=6,
                    )
                if u != root and low[v] >= dfn[u]:
                    articulation.add(u)
                    tracer.mark(
                        f"node:{u}",
                        deps=[f"low[{v}]", f"dfn[{u}]"],
                        state=snapshot(),
                        role="articulation",
                        reason="存在子树无法回到 u 的祖先，因此 u 是割点。",
                        code_line=7,
                    )
            else:
                if dfn[v] < low[u]:
                    low[u] = dfn[v]
                    tracer.set(
                        f"low[{u}]",
                        value=low[u],
                        deps=[f"dfn[{v}]", f"edge:{u}->{v}"],
                        state=snapshot(),
                        role="current",
                        reason="返祖边更新 low[u]。",
                        code_line=9,
                    )
        if u == root and child_count > 1:
            articulation.add(u)
            tracer.mark(
                f"node:{u}",
                deps=[f"dfn[{u}]"],
                state=snapshot(),
                role="articulation",
                reason="DFS 根节点有两个以上子树，因此是割点。",
                code_line=10,
            )

    for node in graph:
        if node not in dfn:
            parent[node] = None
            dfs(node, node)
    result = {"articulation": sorted(articulation), "bridges": bridges}
    tracer.result(result)
    return tracer.to_trace()
"""


ARTICULATION_BRIDGES_VERIFIER = ARTICULATION_BRIDGES_CODE.replace("def solve(input_data):", "def verify(input_data):")


BIPARTITE_MATCHING_CODE = """
def solve(input_data):
    graph = input_data["graph"]
    left_nodes = input_data["left"]
    right_match = {}
    left_match = {}

    def dfs(u, visited):
        for v in graph.get(u, []):
            if v in visited:
                continue
            visited.add(v)
            owner = right_match.get(v)
            if owner is None or dfs(owner, visited):
                old = left_match.get(u)
                if old is not None and old != v and right_match.get(old) == u:
                    del right_match[old]
                right_match[v] = u
                left_match[u] = v
                return True
        return False

    for u in left_nodes:
        dfs(u, set())
    return {u: left_match[u] for u in left_nodes if u in left_match}
"""


BIPARTITE_MATCHING_TRACKER = """
def trace(input_data):
    graph = input_data["graph"]
    left_nodes = input_data["left"]
    right_nodes = input_data["right"]
    tracer = Tracer(
        input_data,
        algorithm="二分图匹配",
        pseudocode=["对每个左侧点寻找增广路径", "找到可重配右侧点后更新 match"],
    )
    right_match = {}
    left_match = {}
    active_visited = {}

    def combined_match():
        data = {}
        for left, right in left_match.items():
            data[left] = right
        for right, left in right_match.items():
            data[right] = left
        return data

    def snapshot():
        return {
            "graph": graph,
            "left_nodes": left_nodes[:],
            "right_nodes": right_nodes[:],
            "match": combined_match(),
            "visited": dict(active_visited),
        }

    tracer.create("graph", state=snapshot(), reason="初始化二分图匹配的 match 和 visited。", code_line=1)

    def dfs(u, visited):
        for v in graph.get(u, []):
            tracer.compare(
                [f"edge:{u}->{v}"],
                deps=[f"node:{u}", f"node:{v}"],
                state=snapshot(),
                role="candidate",
                reason="尝试把左侧点连接到右侧点，寻找增广路径。",
                code_line=3,
            )
            if v in visited:
                continue
            visited.add(v)
            active_visited[v] = True
            tracer.mark(
                f"node:{v}",
                deps=[f"edge:{u}->{v}"],
                state=snapshot(),
                role="visited",
                reason="右侧点在本轮增广搜索中被访问。",
                code_line=4,
            )
            owner = right_match.get(v)
            if owner is None or dfs(owner, visited):
                old = left_match.get(u)
                if old is not None and old != v and right_match.get(old) == u:
                    del right_match[old]
                right_match[v] = u
                left_match[u] = v
                tracer.set(
                    f"match[{u}]",
                    value=v,
                    deps=[f"edge:{u}->{v}", f"node:{u}", f"node:{v}"],
                    state=snapshot(),
                    role="answer",
                    reason="增广路径成功，更新左侧点的匹配。",
                    code_line=6,
                )
                tracer.set(
                    f"match[{v}]",
                    value=u,
                    deps=[f"match[{u}]"],
                    state=snapshot(),
                    role="answer",
                    reason="保持右侧点与左侧点的匹配关系一致。",
                    code_line=6,
                )
                return True
        return False

    for u in left_nodes:
        active_visited = {}
        dfs(u, set())
    result = {u: left_match[u] for u in left_nodes if u in left_match}
    tracer.result(result)
    return tracer.to_trace()
"""


BIPARTITE_MATCHING_VERIFIER = BIPARTITE_MATCHING_CODE.replace("def solve(input_data):", "def verify(input_data):")


EDMONDS_KARP_CODE = """
def solve(input_data):
    graph = input_data["graph"]
    capacity = input_data["capacity"]
    source = input_data["source"]
    sink = input_data["sink"]
    flow = {edge: 0 for edge in capacity}
    max_flow = 0

    while True:
        parent = {source: None}
        queue = [source]
        head = 0
        bottleneck = {source: 10 ** 18}
        while head < len(queue) and sink not in parent:
            u = queue[head]
            head += 1
            for v in graph.get(u, []):
                key = f"{u}->{v}"
                residual = capacity.get(key, 0) - flow.get(key, 0)
                if residual > 0 and v not in parent:
                    parent[v] = u
                    bottleneck[v] = min(bottleneck[u], residual)
                    queue.append(v)
        if sink not in parent:
            break
        add = bottleneck[sink]
        max_flow += add
        v = sink
        while v != source:
            u = parent[v]
            key = f"{u}->{v}"
            flow[key] = flow.get(key, 0) + add
            v = u
    return max_flow
"""


EDMONDS_KARP_TRACKER = """
def trace(input_data):
    graph = input_data["graph"]
    capacity = input_data["capacity"]
    source = input_data["source"]
    sink = input_data["sink"]
    tracer = Tracer(
        input_data,
        algorithm="Edmonds-Karp 最大流",
        pseudocode=["BFS 寻找残量网络中的最短增广路径", "按瓶颈值增加路径上的 flow"],
    )
    flow = {edge: 0 for edge in capacity}
    max_flow = 0
    parent = {}
    bottleneck_value = 0

    def snapshot(queue=None):
        return {
            "graph": graph,
            "capacity": dict(capacity),
            "cap": dict(capacity),
            "flow": dict(flow),
            "queue": list(queue or []),
            "parent": dict(parent),
            "bottleneck": bottleneck_value,
        }

    tracer.create("queue", state=snapshot([source]), reason="Edmonds-Karp 初始化 BFS 队列，准备在残量网络中找增广路径。", code_line=1)
    while True:
        parent = {source: None}
        queue = [source]
        head = 0
        bottleneck = {source: 10 ** 18}
        found = False
        while head < len(queue) and not found:
            u = queue[head]
            head += 1
            tracer.pop(
                "queue",
                deps=[f"node:{u}"],
                state=snapshot(queue[head:]),
                role="current",
                reason="BFS 弹出队首节点，检查它的残量出边。",
                code_line=3,
            )
            for v in graph.get(u, []):
                key = f"{u}->{v}"
                residual = capacity.get(key, 0) - flow.get(key, 0)
                tracer.compare(
                    [f"edge:{u}->{v}"],
                    deps=[f"cap[{key}]", f"flow[{key}]", f"node:{u}", f"node:{v}"],
                    value=residual,
                    state=snapshot(queue[head:]),
                    role="candidate",
                    reason="检查边的残量容量是否还能继续增广。",
                    code_line=5,
                )
                if residual > 0 and v not in parent:
                    parent[v] = u
                    bottleneck[v] = min(bottleneck[u], residual)
                    bottleneck_value = bottleneck[v]
                    queue.append(v)
                    tracer.set(
                        f"parent[{v}]",
                        value=u,
                        deps=[f"edge:{u}->{v}", f"cap[{key}]", f"flow[{key}]"],
                        state=snapshot(queue[head:]),
                        role="visited",
                        reason="残量为正，记录 BFS 父节点和当前路径瓶颈。",
                        code_line=6,
                    )
                    if v == sink:
                        found = True
                        break
        if sink not in parent:
            tracer.explain(
                "graph",
                state=snapshot([]),
                reason="残量网络中已经找不到从源点到汇点的增广路径。",
                code_line=8,
            )
            break
        add = bottleneck[sink]
        max_flow += add
        path = []
        v = sink
        while v != source:
            u = parent[v]
            path.append((u, v))
            v = u
        for u, v in path:
            key = f"{u}->{v}"
            flow[key] = flow.get(key, 0) + add
        bottleneck_value = add
        for u, v in path:
            key = f"{u}->{v}"
            tracer.set(
                f"flow[{key}]",
                value=flow[key],
                deps=[f"cap[{key}]", f"edge:{u}->{v}"],
                state=snapshot([]),
                role="answer",
                reason="Edmonds-Karp 沿增广路径增加 flow，并保留剩余残量容量。",
                code_line=10,
            )
    tracer.result(max_flow)
    return tracer.to_trace()
"""


EDMONDS_KARP_VERIFIER = EDMONDS_KARP_CODE.replace("def solve(input_data):", "def verify(input_data):")


def cases() -> tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase(
            id="daily_temperatures",
            title="每日温度",
            problem=(
                "LeetCode 739. 每日温度。给定整数数组 temperatures，"
                "返回每一天需要等几天才会出现更高温度；如果之后没有更高温度，则为 0。"
            ),
            family="栈 / 队列 / 单调栈",
            input_contract="输入 temperatures 数组。",
            variant_name="单调栈",
            strategy="维护温度单调递减的下标栈，遇到更高温度时弹栈并写答案。",
            time_complexity="O(n)",
            space_complexity="O(n)",
            expected_layouts=("array", "stack"),
            code=DAILY_TEMPERATURES_CODE,
            tracker_code=DAILY_TEMPERATURES_TRACKER,
            verifier_code=DAILY_TEMPERATURES_VERIFIER,
            samples=(
                BenchmarkInput({"temperatures": [73, 74, 75, 71, 69, 72, 76, 73]}, [1, 1, 4, 2, 1, 1, 0, 0]),
                BenchmarkInput({"temperatures": [30, 40, 50, 60]}, [1, 1, 1, 0]),
                BenchmarkInput({"temperatures": [30, 60, 90]}, [1, 1, 0]),
            ),
        ),
        BenchmarkCase(
            id="binary_tree_inorder",
            title="二叉树中序遍历",
            problem=(
                "给定一棵二叉树 tree，返回其中序遍历节点 id 序列。"
                "tree 使用 nodes 和 edges 表示，edges 的方向是父节点到子节点，子节点顺序表示左右子树。"
            ),
            family="树 / BST / LCA",
            input_contract="输入 tree。",
            variant_name="递归中序遍历",
            strategy="递归进入左子树，访问当前节点，再进入右子树，并展示递归 frame 返回值。",
            time_complexity="O(n)",
            space_complexity="O(h)",
            expected_layouts=("tree",),
            code=BINARY_TREE_INORDER_CODE,
            tracker_code=BINARY_TREE_INORDER_TRACKER,
            verifier_code=BINARY_TREE_INORDER_VERIFIER,
            samples=(
                BenchmarkInput({"tree": {"nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}, {"id": "5"}], "edges": [["1", "2"], ["1", "3"], ["2", "4"], ["2", "5"]]}}, ["4", "2", "5", "1", "3"]),
                BenchmarkInput({"tree": {"nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}], "edges": [["A", "B"], ["A", "C"]]}}, ["B", "A", "C"]),
                BenchmarkInput({"tree": {"nodes": [{"id": "R"}, {"id": "L"}, {"id": "LL"}, {"id": "LR"}], "edges": [["R", "L"], ["L", "LL"], ["L", "LR"]]}}, ["LL", "L", "LR", "R"]),
                BenchmarkInput({"tree": {"nodes": [{"id": "X"}], "edges": []}}, ["X"]),
                BenchmarkInput({"tree": {"nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}, {"id": "5"}, {"id": "6"}], "edges": [["1", "2"], ["2", "3"], ["3", "4"], ["4", "5"], ["5", "6"]]}}, ["6", "5", "4", "3", "2", "1"]),
            ),
        ),
        BenchmarkCase(
            id="lca",
            title="二叉树最近公共祖先",
            problem=(
                "给定一棵二叉树 tree，以及两个节点 p 和 q，返回它们的最近公共祖先节点 id。"
                "tree 使用 nodes 和 edges 表示，edges 的方向是父节点到子节点。"
            ),
            family="树 / BST / LCA",
            input_contract="输入 tree、p、q。",
            variant_name="后序 DFS",
            strategy="DFS 返回当前子树是否命中 p 或 q；左右都命中时当前节点为 LCA。",
            time_complexity="O(n)",
            space_complexity="O(h)",
            expected_layouts=("tree",),
            code=LCA_CODE,
            tracker_code=LCA_TRACKER,
            verifier_code=LCA_VERIFIER,
            samples=(
                BenchmarkInput({"tree": {"nodes": [{"id": "3"}, {"id": "5"}, {"id": "1"}, {"id": "6"}, {"id": "2"}, {"id": "0"}, {"id": "8"}, {"id": "7"}, {"id": "4"}], "edges": [["3", "5"], ["3", "1"], ["5", "6"], ["5", "2"], ["1", "0"], ["1", "8"], ["2", "7"], ["2", "4"]]}, "p": "5", "q": "1"}, "3"),
                BenchmarkInput({"tree": {"nodes": [{"id": "3"}, {"id": "5"}, {"id": "1"}, {"id": "6"}, {"id": "2"}, {"id": "7"}, {"id": "4"}], "edges": [["3", "5"], ["3", "1"], ["5", "6"], ["5", "2"], ["2", "7"], ["2", "4"]]}, "p": "7", "q": "4"}, "2"),
                BenchmarkInput({"tree": {"nodes": [{"id": "3"}, {"id": "5"}, {"id": "1"}, {"id": "6"}, {"id": "2"}, {"id": "7"}, {"id": "4"}], "edges": [["3", "5"], ["3", "1"], ["5", "6"], ["5", "2"], ["2", "7"], ["2", "4"]]}, "p": "6", "q": "4"}, "5"),
                BenchmarkInput({"tree": {"nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}], "edges": [["A", "B"], ["B", "C"], ["C", "D"]]}, "p": "B", "q": "D"}, "B"),
                BenchmarkInput({"tree": {"nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}, {"id": "E"}], "edges": [["A", "B"], ["A", "C"], ["C", "D"], ["C", "E"]]}, "p": "D", "q": "E"}, "C"),
            ),
        ),
        BenchmarkCase(
            id="tree_diameter",
            title="二叉树直径",
            problem=(
                "给定一棵二叉树 tree，返回任意两个节点之间最长路径的边数。"
                "需要后序聚合每个子树高度，并用两个最大子树高度更新直径。"
            ),
            family="树 / BST / LCA",
            input_contract="输入 tree。",
            variant_name="后序高度聚合",
            strategy="每个递归 frame 返回子树高度，父节点用两个最大子树高度更新全局直径。",
            time_complexity="O(n)",
            space_complexity="O(h)",
            expected_layouts=("tree",),
            code=TREE_DIAMETER_CODE,
            tracker_code=TREE_DIAMETER_TRACKER,
            verifier_code=TREE_DIAMETER_VERIFIER,
            samples=(
                BenchmarkInput({"tree": {"nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}, {"id": "5"}], "edges": [["1", "2"], ["1", "3"], ["2", "4"], ["2", "5"]]}}, 3),
                BenchmarkInput({"tree": {"nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}], "edges": [["1", "2"], ["2", "3"], ["3", "4"]]}}, 3),
                BenchmarkInput({"tree": {"nodes": [{"id": "A"}], "edges": []}}, 0),
                BenchmarkInput({"tree": {"nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}, {"id": "5"}, {"id": "6"}], "edges": [["1", "2"], ["1", "3"], ["2", "4"], ["4", "5"], ["3", "6"]]}}, 5),
            ),
        ),
        BenchmarkCase(
            id="tree_max_independent_set",
            title="树形 DP 最大独立集",
            problem=(
                "给定一棵带权树 tree，选择若干不相邻节点，使权重和最大，返回最大权重。"
                "需要展示 dp_take 和 dp_skip 的子树聚合过程。"
            ),
            family="树形 DP",
            input_contract="输入带 value 权重的 tree。",
            variant_name="树形 DP take/skip",
            strategy="dp_take[u] 表示选择 u 的最优值，dp_skip[u] 表示不选择 u 的最优值。",
            time_complexity="O(n)",
            space_complexity="O(n)",
            expected_layouts=("tree",),
            code=TREE_MAX_INDEPENDENT_SET_CODE,
            tracker_code=TREE_MAX_INDEPENDENT_SET_TRACKER,
            verifier_code=TREE_MAX_INDEPENDENT_SET_VERIFIER,
            samples=(
                BenchmarkInput({"tree": {"nodes": [{"id": "1", "value": 3}, {"id": "2", "value": 2}, {"id": "3", "value": 1}, {"id": "4", "value": 10}, {"id": "5", "value": 1}], "edges": [["1", "2"], ["1", "3"], ["2", "4"], ["2", "5"]]}}, 14),
                BenchmarkInput({"tree": {"nodes": [{"id": "A", "value": 5}, {"id": "B", "value": 4}, {"id": "C", "value": 6}], "edges": [["A", "B"], ["A", "C"]]}}, 10),
                BenchmarkInput({"tree": {"nodes": [{"id": "R", "value": 1}, {"id": "L", "value": 10}, {"id": "M", "value": 1}, {"id": "N", "value": 10}], "edges": [["R", "L"], ["R", "M"], ["M", "N"]]}}, 20),
                BenchmarkInput({"tree": {"nodes": [{"id": "X", "value": 7}], "edges": []}}, 7),
            ),
        ),
        BenchmarkCase(
            id="kth_largest",
            title="数组中的第 K 个最大元素",
            problem=(
                "LeetCode 215. 给定整数数组 nums 和整数 k，返回数组中第 k 个最大的元素。"
                "希望使用容量为 k 的小顶堆。"
            ),
            family="堆 / TopK / Huffman",
            input_contract="输入 nums 数组和 k。",
            variant_name="小顶堆 TopK",
            strategy="维护容量为 k 的小顶堆，堆顶就是当前第 k 大。",
            time_complexity="O(n log k)",
            space_complexity="O(k)",
            expected_layouts=("array", "heap"),
            code=KTH_LARGEST_CODE,
            tracker_code=KTH_LARGEST_TRACKER,
            verifier_code=KTH_LARGEST_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [3, 2, 1, 5, 6, 4], "k": 2}, 5),
                BenchmarkInput({"nums": [3, 2, 3, 1, 2, 4, 5, 5, 6], "k": 4}, 4),
                BenchmarkInput({"nums": [1], "k": 1}, 1),
                BenchmarkInput({"nums": [-1, -3, 2, 0], "k": 2}, 0),
                BenchmarkInput({"nums": [7, 7, 7], "k": 2}, 7),
                BenchmarkInput({"nums": [9, 1, 8, 2, 7, 3], "k": 3}, 7),
                BenchmarkInput({"nums": [10, 4, 6, 8], "k": 4}, 4),
                BenchmarkInput({"nums": [5, -2, 11, 11, 0], "k": 1}, 11),
            ),
        ),
        BenchmarkCase(
            id="trie_prefix",
            title="Trie 前缀计数",
            problem=(
                "给定字符串数组 words 和前缀 prefix，使用 Trie 思路统计有多少单词以 prefix 开头。"
            ),
            family="Trie",
            input_contract="输入 words 和 prefix。",
            variant_name="Trie 插入与前缀统计",
            strategy="把所有单词插入 Trie，再沿前缀路径统计匹配数量。",
            time_complexity="O(总字符数)",
            space_complexity="O(总字符数)",
            expected_layouts=("trie",),
            code=TRIE_PREFIX_CODE,
            tracker_code=TRIE_PREFIX_TRACKER,
            verifier_code=TRIE_PREFIX_VERIFIER,
            samples=(
                BenchmarkInput({"words": ["apple", "app", "ape", "bat"], "prefix": "ap"}, 3),
                BenchmarkInput({"words": ["dog", "door", "deer"], "prefix": "doo"}, 1),
                BenchmarkInput({"words": ["cat", "car", "dog"], "prefix": "z"}, 0),
                BenchmarkInput({"words": ["a"], "prefix": "a"}, 1),
                BenchmarkInput({"words": ["same", "same", "sample"], "prefix": "sam"}, 3),
                BenchmarkInput({"words": ["team", "tear", "tea", "to"], "prefix": "tea"}, 3),
                BenchmarkInput({"words": ["alpha", "beta"], "prefix": ""}, 2),
                BenchmarkInput({"words": ["prefix", "pre", "prevent", "post"], "prefix": "pre"}, 3),
            ),
        ),
        BenchmarkCase(
            id="provinces",
            title="省份数量",
            problem=(
                "LeetCode 547. 省份数量。给定城市连通矩阵 isConnected，"
                "如果两个城市直接或间接相连，则属于同一个省份。返回省份数量。"
            ),
            family="并查集",
            input_contract="输入 isConnected 矩阵。",
            variant_name="并查集合并",
            strategy="相连城市执行 union，最后统计根节点数量。",
            time_complexity="O(n^2 α(n))",
            space_complexity="O(n)",
            expected_layouts=("matrix", "union_find"),
            code=PROVINCES_CODE,
            tracker_code=PROVINCES_TRACKER,
            verifier_code=PROVINCES_VERIFIER,
            samples=(
                BenchmarkInput({"isConnected": [[1, 1, 0], [1, 1, 0], [0, 0, 1]]}, 2),
                BenchmarkInput({"isConnected": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}, 3),
            ),
        ),
        BenchmarkCase(
            id="permutations",
            title="全排列",
            problem=(
                "LeetCode 46. 全排列。给定不含重复数字的数组 nums，返回所有可能的排列。"
            ),
            family="回溯 / 递归",
            input_contract="输入 nums 数组。",
            variant_name="回溯搜索树",
            strategy="用 path 保存当前选择，递归选择未使用数字，返回时撤销选择。",
            time_complexity="O(n! n)",
            space_complexity="O(n)",
            expected_layouts=("array", "recursion_tree"),
            code=PERMUTATIONS_CODE,
            tracker_code=PERMUTATIONS_TRACKER,
            verifier_code=PERMUTATIONS_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [1, 2, 3]}, [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]),
                BenchmarkInput({"nums": [0, 1]}, [[0, 1], [1, 0]]),
                BenchmarkInput({"nums": [1]}, [[1]]),
                BenchmarkInput({"nums": [6]}, [[6]]),
                BenchmarkInput({"nums": [-1, 2]}, [[-1, 2], [2, -1]]),
                BenchmarkInput({"nums": [1, 2]}, [[1, 2], [2, 1]]),
                BenchmarkInput({"nums": [2, 3, 4]}, [[2, 3, 4], [2, 4, 3], [3, 2, 4], [3, 4, 2], [4, 2, 3], [4, 3, 2]]),
                BenchmarkInput({"nums": [4, 5]}, [[4, 5], [5, 4]]),
                BenchmarkInput({"nums": [7, 8]}, [[7, 8], [8, 7]]),
                BenchmarkInput({"nums": [9]}, [[9]]),
                BenchmarkInput({"nums": [0]}, [[0]]),
                BenchmarkInput({"nums": [-2]}, [[-2]]),
            ),
        ),
        BenchmarkCase(
            id="convex_hull",
            title="凸包",
            problem=(
                "给定二维点集 points，返回这些点的凸包顶点，按 Andrew 单调链算法的输出顺序排列。"
            ),
            family="几何 / 扫描线",
            input_contract="输入 points 二维点数组。",
            variant_name="Andrew 单调链",
            strategy="按坐标排序点集，分别维护上下凸壳，使用 orientation/cross 判断转向。",
            time_complexity="O(n log n)",
            space_complexity="O(n)",
            expected_layouts=("geometry",),
            code=CONVEX_HULL_CODE,
            tracker_code=CONVEX_HULL_TRACKER,
            verifier_code=CONVEX_HULL_VERIFIER,
            samples=(
                BenchmarkInput({"points": [[0, 0], [1, 1], [2, 0], [1, 2]]}, [[0, 0], [2, 0], [1, 2]]),
                BenchmarkInput({"points": [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]}, [[0, 0], [1, 0], [1, 1], [0, 1]]),
            ),
        ),
        BenchmarkCase(
            id="segment_tree_range_sum",
            title="线段树区间和",
            problem=(
                "给定整数数组 nums、闭区间 query=[l,r] 和单点赋值 update=[pos,value]，"
                "使用线段树先查询更新前区间和，再执行单点更新并查询更新后区间和。"
            ),
            family="区间结构",
            input_contract="输入 nums 数组、query 闭区间和 update 单点赋值。",
            variant_name="线段树区间和 + 单点更新",
            strategy="线段树节点 meta 记录覆盖区间与区间和，查询区间沿覆盖节点求和，更新路径从叶子回溯维护父节点。",
            time_complexity="O(log n)",
            space_complexity="O(n)",
            expected_layouts=("tree", "array"),
            code=SEGMENT_TREE_RANGE_SUM_CODE,
            tracker_code=SEGMENT_TREE_RANGE_SUM_TRACKER,
            verifier_code=SEGMENT_TREE_RANGE_SUM_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [2, 1, 4, 5], "query": [1, 3], "update": [2, 6]}, {"before": 10, "after": 12}),
                BenchmarkInput({"nums": [3, -1, 2, 7, 4], "query": [0, 2], "update": [1, 5]}, {"before": 4, "after": 10}),
            ),
        ),
        BenchmarkCase(
            id="fenwick_tree_prefix_sum",
            title="树状数组前缀和",
            problem=(
                "给定整数数组 nums、闭区间 query=[l,r] 和单点增量 update=[pos,delta]，"
                "使用树状数组先查询更新前区间和，再执行单点增量更新并查询更新后区间和。"
            ),
            family="区间结构",
            input_contract="输入 nums 数组、query 闭区间和 update 单点增量。",
            variant_name="树状数组前缀和 + 单点增量",
            strategy="bit[i] 保存 lowbit 覆盖块，区间和由两个前缀和相减，更新沿 lowbit 路径向后同步。",
            time_complexity="O(log n)",
            space_complexity="O(n)",
            expected_layouts=("array",),
            code=FENWICK_TREE_PREFIX_SUM_CODE,
            tracker_code=FENWICK_TREE_PREFIX_SUM_TRACKER,
            verifier_code=FENWICK_TREE_PREFIX_SUM_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [1, 2, 3, 4, 5], "query": [1, 3], "update": [2, 4]}, {"before": 9, "after": 13}),
                BenchmarkInput({"nums": [5, -2, 6, 1], "query": [0, 2], "update": [1, 3]}, {"before": 9, "after": 12}),
            ),
        ),
        BenchmarkCase(
            id="sparse_table_range_min",
            title="稀疏表区间最小值",
            problem=(
                "给定整数数组 nums 和闭区间 query=[l,r]，使用稀疏表预处理固定长度区间最小值，"
                "再用两个重叠区间回答区间最小值查询。"
            ),
            family="区间结构",
            input_contract="输入 nums 数组和 query 闭区间。",
            variant_name="稀疏表 RMQ",
            strategy="st[k][i] 记录长度 2^k 区间最小值，查询时选择 k=log(length) 并合并两个重叠区间。",
            time_complexity="O(n log n) build, O(1) query",
            space_complexity="O(n log n)",
            expected_layouts=("matrix", "array"),
            code=SPARSE_TABLE_RANGE_MIN_CODE,
            tracker_code=SPARSE_TABLE_RANGE_MIN_TRACKER,
            verifier_code=SPARSE_TABLE_RANGE_MIN_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [5, 2, 7, 3, 6, 1], "query": [1, 4]}, 2),
                BenchmarkInput({"nums": [8, 4, 9, 0, 3], "query": [2, 4]}, 0),
            ),
        ),
        BenchmarkCase(
            id="gcd_euclid",
            title="最大公约数",
            problem="给定两个非负整数 a 和 b，使用 Euclid 算法返回它们的最大公约数。",
            family="数学与位运算",
            input_contract="输入整数 a 和 b。",
            variant_name="Euclid 辗转相除",
            strategy="反复使用 gcd(a,b)=gcd(b,a mod b)，直到余数为 0。",
            time_complexity="O(log min(a,b))",
            space_complexity="O(1)",
            expected_layouts=("array",),
            code=GCD_EUCLID_CODE,
            tracker_code=GCD_EUCLID_TRACKER,
            verifier_code=GCD_EUCLID_VERIFIER,
            samples=(
                BenchmarkInput({"a": 48, "b": 18}, 6),
                BenchmarkInput({"a": 270, "b": 192}, 6),
                BenchmarkInput({"a": 17, "b": 0}, 17),
            ),
        ),
        BenchmarkCase(
            id="fast_power_mod",
            title="快速幂取模",
            problem="给定 base、exponent 和 mod，使用快速幂返回 base^exponent mod mod。",
            family="数学与位运算",
            input_contract="输入 base、exponent、mod。",
            variant_name="二进制快速幂",
            strategy="把指数拆成二进制，维护 powers 平方表，遇到 1 位就乘入答案。",
            time_complexity="O(log exponent)",
            space_complexity="O(log exponent)",
            expected_layouts=("array",),
            code=FAST_POWER_MOD_CODE,
            tracker_code=FAST_POWER_MOD_TRACKER,
            verifier_code=FAST_POWER_MOD_VERIFIER,
            samples=(
                BenchmarkInput({"base": 3, "exponent": 5, "mod": 13}, 9),
                BenchmarkInput({"base": 2, "exponent": 10, "mod": 1000}, 24),
                BenchmarkInput({"base": 7, "exponent": 0, "mod": 5}, 1),
            ),
        ),
        BenchmarkCase(
            id="sieve_primes",
            title="埃氏筛",
            problem="给定整数 n，使用埃氏筛返回不超过 n 的所有质数。",
            family="数学与位运算",
            input_contract="输入整数 n。",
            variant_name="倍数标记筛法",
            strategy="从每个质数 p 的 p*p 开始标记倍数为合数，剩余 True 下标为质数。",
            time_complexity="O(n log log n)",
            space_complexity="O(n)",
            expected_layouts=("array",),
            code=SIEVE_PRIMES_CODE,
            tracker_code=SIEVE_PRIMES_TRACKER,
            verifier_code=SIEVE_PRIMES_VERIFIER,
            samples=(
                BenchmarkInput({"n": 20}, [2, 3, 5, 7, 11, 13, 17, 19]),
                BenchmarkInput({"n": 10}, [2, 3, 5, 7]),
                BenchmarkInput({"n": 1}, []),
            ),
        ),
        BenchmarkCase(
            id="combinations_pascal",
            title="组合数",
            problem="给定 n 和 k，使用帕斯卡恒等式计算组合数 C(n,k)。",
            family="数学与位运算",
            input_contract="输入整数 n 和 k。",
            variant_name="Pascal DP 表",
            strategy="用 table[i][j] 表示 C(i,j)，由 C(i-1,j-1)+C(i-1,j) 转移。",
            time_complexity="O(nk)",
            space_complexity="O(nk)",
            expected_layouts=("matrix",),
            code=COMBINATIONS_PASCAL_CODE,
            tracker_code=COMBINATIONS_PASCAL_TRACKER,
            verifier_code=COMBINATIONS_PASCAL_VERIFIER,
            samples=(
                BenchmarkInput({"n": 5, "k": 2}, 10),
                BenchmarkInput({"n": 6, "k": 3}, 20),
                BenchmarkInput({"n": 4, "k": 0}, 1),
            ),
        ),
        BenchmarkCase(
            id="bitmask_subsets",
            title="位掩码枚举子集",
            problem="给定数组 nums，使用二进制 mask 枚举所有子集。",
            family="数学与位运算",
            input_contract="输入 nums 数组。",
            variant_name="二进制子集枚举",
            strategy="mask 的第 i 位表示是否选择 nums[i]，从 0 到 2^n-1 枚举所有子集。",
            time_complexity="O(n 2^n)",
            space_complexity="O(n 2^n)",
            expected_layouts=("array",),
            code=BITMASK_SUBSETS_CODE,
            tracker_code=BITMASK_SUBSETS_TRACKER,
            verifier_code=BITMASK_SUBSETS_VERIFIER,
            samples=(
                BenchmarkInput({"nums": [1, 2, 3]}, [[], [1], [2], [1, 2], [3], [1, 3], [2, 3], [1, 2, 3]]),
                BenchmarkInput({"nums": [0, 1]}, [[], [0], [1], [0, 1]]),
            ),
        ),
        BenchmarkCase(
            id="lowbit_decomposition",
            title="lowbit 分解",
            problem="给定整数 n，每次取 lowbit(n)=n&-n 并删除最低位的 1，返回分解出的 lowbit 序列。",
            family="数学与位运算",
            input_contract="输入整数 n。",
            variant_name="lowbit 拆位",
            strategy="反复取最低位的 1 所代表的值，并从 remaining 中减去该值。",
            time_complexity="O(popcount(n))",
            space_complexity="O(popcount(n))",
            expected_layouts=("array",),
            code=LOWBIT_DECOMPOSITION_CODE,
            tracker_code=LOWBIT_DECOMPOSITION_TRACKER,
            verifier_code=LOWBIT_DECOMPOSITION_VERIFIER,
            samples=(
                BenchmarkInput({"n": 12}, [4, 8]),
                BenchmarkInput({"n": 13}, [1, 4, 8]),
                BenchmarkInput({"n": 0}, []),
            ),
        ),
        BenchmarkCase(
            id="tarjan_scc",
            title="Tarjan 强连通分量",
            problem="给定有向图 graph，使用 Tarjan 算法返回图中的强连通分量。",
            family="图高级",
            input_contract="输入有向图邻接表 graph。",
            variant_name="Tarjan SCC",
            strategy="DFS 写入 dfn/low，使用 stack 维护当前搜索栈，low==dfn 时弹出一个强连通分量。",
            time_complexity="O(V+E)",
            space_complexity="O(V)",
            expected_layouts=("graph", "stack", "map"),
            code=TARJAN_SCC_CODE,
            tracker_code=TARJAN_SCC_TRACKER,
            verifier_code=TARJAN_SCC_VERIFIER,
            samples=(
                BenchmarkInput({"graph": {"A": ["B"], "B": ["C", "D"], "C": ["A"], "D": ["E"], "E": ["D"]}}, [["E", "D"], ["C", "B", "A"]]),
                BenchmarkInput({"graph": {"1": ["2"], "2": ["3"], "3": ["1"], "4": []}}, [["3", "2", "1"], ["4"]]),
            ),
        ),
        BenchmarkCase(
            id="articulation_bridges",
            title="割点和桥",
            problem="给定无向图 graph，使用 Tarjan dfn/low 返回所有割点和桥。",
            family="图高级",
            input_contract="输入无向图邻接表 graph。",
            variant_name="Tarjan 割点和桥",
            strategy="DFS 维护 dfn/low/parent；low[child] > dfn[u] 判定桥，low[child] >= dfn[u] 判定割点。",
            time_complexity="O(V+E)",
            space_complexity="O(V)",
            expected_layouts=("graph", "map"),
            code=ARTICULATION_BRIDGES_CODE,
            tracker_code=ARTICULATION_BRIDGES_TRACKER,
            verifier_code=ARTICULATION_BRIDGES_VERIFIER,
            samples=(
                BenchmarkInput({"graph": {"A": ["B"], "B": ["A", "C", "D"], "C": ["B", "D"], "D": ["B", "C", "E"], "E": ["D"]}}, {"articulation": ["B", "D"], "bridges": [["D", "E"], ["A", "B"]]}),
                BenchmarkInput({"graph": {"1": ["2"], "2": ["1", "3"], "3": ["2"]}}, {"articulation": ["2"], "bridges": [["2", "3"], ["1", "2"]]}),
            ),
        ),
        BenchmarkCase(
            id="bipartite_matching",
            title="二分图匹配",
            problem="给定二分图的左侧点、右侧点和邻接表 graph，使用增广路径求最大匹配。",
            family="图高级",
            input_contract="输入 graph、left、right。",
            variant_name="DFS 增广路径匹配",
            strategy="逐个左侧点寻找增广路径，成功后更新 match 映射。",
            time_complexity="O(VE)",
            space_complexity="O(V)",
            expected_layouts=("graph", "map"),
            code=BIPARTITE_MATCHING_CODE,
            tracker_code=BIPARTITE_MATCHING_TRACKER,
            verifier_code=BIPARTITE_MATCHING_VERIFIER,
            samples=(
                BenchmarkInput({"graph": {"L1": ["R1", "R2"], "L2": ["R1"], "L3": ["R2"]}, "left": ["L1", "L2", "L3"], "right": ["R1", "R2"]}, {"L1": "R2", "L2": "R1"}),
                BenchmarkInput({"graph": {"A": ["X"], "B": ["X", "Y"]}, "left": ["A", "B"], "right": ["X", "Y"]}, {"A": "X", "B": "Y"}),
            ),
        ),
        BenchmarkCase(
            id="edmonds_karp",
            title="Edmonds-Karp 最大流",
            problem="给定有向网络的 graph、capacity、source 和 sink，使用 Edmonds-Karp 教学版返回最大流。",
            family="图高级",
            input_contract="输入 graph、capacity、source、sink。",
            variant_name="BFS 增广路径最大流",
            strategy="在残量网络中 BFS 寻找最短增广路径，再按瓶颈容量增加 flow。",
            time_complexity="O(VE^2)",
            space_complexity="O(E)",
            expected_layouts=("graph", "queue", "map"),
            code=EDMONDS_KARP_CODE,
            tracker_code=EDMONDS_KARP_TRACKER,
            verifier_code=EDMONDS_KARP_VERIFIER,
            samples=(
                BenchmarkInput({"graph": {"S": ["A", "B"], "A": ["T"], "B": ["T"], "T": []}, "capacity": {"S->A": 2, "S->B": 1, "A->T": 2, "B->T": 1}, "source": "S", "sink": "T"}, 3),
                BenchmarkInput({"graph": {"S": ["A"], "A": ["B", "T"], "B": ["T"], "T": []}, "capacity": {"S->A": 3, "A->B": 2, "A->T": 1, "B->T": 2}, "source": "S", "sink": "T"}, 3),
            ),
        ),
    )
