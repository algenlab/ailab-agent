"""Benchmark cases: graph."""

from __future__ import annotations

from tests.benchmark_cases import BenchmarkCase, BenchmarkInput

GRAPH_BFS_CODE = """
def solve(input_data):
    graph = input_data["graph"]
    start = input_data["start"]
    dist = {start: 0}
    queue = [start]
    head = 0
    while head < len(queue):
        cur = queue[head]
        head += 1
        for nei in graph.get(cur, []):
            if nei not in dist:
                dist[nei] = dist[cur] + 1
                queue.append(nei)
    return dist
"""


GRAPH_BFS_TRACKER = """
def trace(input_data):
    graph = input_data["graph"]
    start = input_data["start"]
    dist = {start: 0}
    queue = [start]
    head = 0
    events = [{"step": 0, "op": "create", "targets": [{"id": "queue"}, {"id": f"node:{start}"}], "state": {"graph": graph, "queue": queue[:], "dist": dict(dist)}, "role": "current", "reason": "起点入队，距离为 0。", "code_line": 1}]
    while head < len(queue):
        cur = queue[head]
        head += 1
        events.append({"step": len(events), "op": "pop", "targets": [{"id": "queue"}, {"id": f"node:{cur}"}], "state": {"graph": graph, "queue": queue[head:], "dist": dict(dist)}, "role": "current", "reason": "取出队首节点并检查邻居。", "code_line": 4})
        for nei in graph.get(cur, []):
            events.append({"step": len(events), "op": "compare", "targets": [{"id": f"edge:{cur}->{nei}"}], "deps": [{"id": f"node:{cur}"}, {"id": f"node:{nei}"}], "state": {"graph": graph, "queue": queue[head:], "dist": dict(dist), "current": cur, "neighbor": nei}, "role": "candidate", "reason": "检查当前边是否通向未访问节点。", "code_line": 6})
            if nei not in dist:
                dist[nei] = dist[cur] + 1
                queue.append(nei)
                events.append({"step": len(events), "op": "mark", "targets": [{"id": f"node:{nei}"}], "deps": [{"id": f"node:{cur}"}], "state": {"graph": graph, "queue": queue[head:], "dist": dict(dist)}, "role": "visited", "reason": "首次发现邻居，记录距离并入队。", "code_line": 7})
    return {"schema_version": "semantic-trace-v1", "algorithm": "BFS 最短层数", "input_data": input_data, "result": dist, "pseudocode": ["队列按层扩展", "首次访问时记录距离"], "events": events}
"""


GRAPH_BFS_VERIFIER = """
def verify(input_data):
    graph = input_data["graph"]
    start = input_data["start"]
    dist = {start: 0}
    frontier = [start]
    while frontier:
        nxt = []
        for cur in frontier:
            for nei in graph.get(cur, []):
                if nei not in dist:
                    dist[nei] = dist[cur] + 1
                    nxt.append(nei)
        frontier = nxt
    return dist
"""


GRAPH_DFS_TRAVERSAL_CODE = """
def solve(input_data):
    graph = input_data["graph"]
    start = input_data["start"]
    order = []
    seen = set()
    def dfs(node):
        seen.add(node)
        order.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in seen:
                dfs(neighbor)
    dfs(start)
    return order
"""


GRAPH_DFS_TRAVERSAL_TRACKER = """
def trace(input_data):
    graph = input_data["graph"]
    start = input_data["start"]
    tracer = Tracer(input_data, algorithm="DFS 图遍历", pseudocode=["进入节点", "递归访问未访问邻居", "退出节点"], policy="full", max_events=180)
    expected_nodes = []
    probe_stack = [start]
    probe_seen = set()
    while probe_stack:
        probe_node = probe_stack.pop()
        if probe_node in probe_seen:
            continue
        probe_seen.add(probe_node)
        expected_nodes.append(probe_node)
        for probe_neighbor in reversed(graph.get(probe_node, [])):
            if probe_neighbor not in probe_seen:
                probe_stack.append(probe_neighbor)
    contract = {"submode": "dfs", "source": start, "expected_nodes": expected_nodes}
    seen = set()
    order = []
    stack = []

    def state(current=None):
        return {
            "graph": graph,
            "stack": stack[:],
            "visited": {node: node in seen for node in graph},
            "dfs_order": order[:],
            "current": current,
            "graph_contract": contract,
        }

    tracer.create("stack", state=state(start), reason="初始化 DFS 调用栈。", code_line=1)

    def dfs(node):
        stack.append(node)
        seen.add(node)
        order.append(node)
        tracer.enter(f"frame:dfs({node})", deps=[f"node:{node}"], state=state(node), role="current", reason="进入 DFS 递归帧并标记节点。", code_line=3)
        for neighbor in graph.get(node, []):
            tracer.compare([f"edge:{node}->{neighbor}", f"node:{neighbor}"], deps=[f"node:{node}"], state=state(node), role="candidate", reason="检查邻居是否已经访问。", code_line=6)
            if neighbor not in seen:
                dfs(neighbor)
        stack.pop()
        tracer.exit(f"frame:dfs({node})", value=node, deps=[f"node:{node}"], state=state(node), role="current", reason="当前节点所有邻居处理完毕，退出递归帧。", code_line=8)

    dfs(start)
    tracer.mark("dfs_order", value=order[:], state=state(), role="answer", reason="DFS 遍历完成，返回访问顺序。", code_line=9)
    tracer.result(order)
    return tracer.to_trace()
"""


GRAPH_DFS_TRAVERSAL_VERIFIER = """
def verify(input_data):
    graph = input_data["graph"]
    start = input_data["start"]
    order = []
    visited = {start}
    stack = [(start, 0)]
    order.append(start)
    while stack:
        node, index = stack[-1]
        neighbors = graph.get(node, [])
        if index >= len(neighbors):
            stack.pop()
            continue
        neighbor = neighbors[index]
        stack[-1] = (node, index + 1)
        if neighbor in visited:
            continue
        visited.add(neighbor)
        order.append(neighbor)
        stack.append((neighbor, 0))
    return order
"""


GRAPH_CONNECTED_COMPONENTS_CODE = """
def solve(input_data):
    graph = input_data["graph"]
    seen = set()
    components = []
    nodes = sorted({str(node) for node in graph} | {str(nei) for neighbors in graph.values() for nei in neighbors})
    def neighbors(node):
        out = set(str(nei) for nei in graph.get(node, []))
        for src, items in graph.items():
            if node in [str(nei) for nei in items]:
                out.add(str(src))
        return sorted(out)
    for node in nodes:
        if node in seen:
            continue
        stack = [node]
        seen.add(node)
        component = []
        while stack:
            cur = stack.pop()
            component.append(cur)
            for nei in reversed(neighbors(cur)):
                if nei not in seen:
                    seen.add(nei)
                    stack.append(nei)
        components.append(sorted(component))
    return components
"""


GRAPH_CONNECTED_COMPONENTS_TRACKER = """
def trace(input_data):
    graph = input_data["graph"]
    tracer = Tracer(input_data, algorithm="连通分量", pseudocode=["从未访问节点开始 DFS", "收集一个连通分量", "继续下一个未访问节点"], policy="full", max_events=220)
    contract = {"submode": "connected_components", "expected_nodes": sorted(graph)}
    seen = set()
    components = []
    nodes = sorted({str(node) for node in graph} | {str(nei) for neighbors in graph.values() for nei in neighbors})

    def graph_neighbors(node):
        result = set(str(nei) for nei in graph.get(node, []))
        for src, items in graph.items():
            if node in [str(nei) for nei in items]:
                result.add(str(src))
        return sorted(result)

    def state(current=None, component=None):
        return {
            "graph": graph,
            "visited": {node: node in seen for node in nodes},
            "components": [part[:] for part in components],
            "component": component[:] if component else [],
            "current": current,
            "graph_contract": contract,
        }

    tracer.create("graph", state=state(), reason="初始化所有节点为未访问。", code_line=1)
    for node in nodes:
        if node in seen:
            continue
        stack = [node]
        seen.add(node)
        component = []
        tracer.enter(f"frame:component({node})", deps=[f"node:{node}"], state=state(node, component), role="current", reason="发现新的连通分量起点。", code_line=5)
        while stack:
            cur = stack.pop()
            component.append(cur)
            tracer.mark(f"node:{cur}", value=cur, deps=[f"frame:component({node})"], state=state(cur, component), role="visited", reason="把当前节点加入正在收集的连通分量。", code_line=10)
            for nei in graph_neighbors(cur):
                tracer.compare([f"edge:{cur}->{nei}", f"node:{nei}"], deps=[f"node:{cur}"], state=state(cur, component), role="candidate", reason="检查相邻节点是否属于同一连通分量。", code_line=11)
                if nei not in seen:
                    seen.add(nei)
                    stack.append(nei)
        components.append(sorted(component))
        tracer.exit(f"frame:component({node})", value=sorted(component), state=state(node, component), role="answer", reason="当前连通分量收集完成。", code_line=14)
    tracer.mark("components", value=[part[:] for part in components], state=state(), role="answer", reason="所有连通分量收集完成。", code_line=15)
    tracer.result(components)
    return tracer.to_trace()
"""


GRAPH_CONNECTED_COMPONENTS_VERIFIER = """
def verify(input_data):
    graph = input_data["graph"]
    nodes = set(str(node) for node in graph)
    for neighbors in graph.values():
        for neighbor in neighbors:
            nodes.add(str(neighbor))
    parent = {node: node for node in nodes}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(str(a)), find(str(b))
        if ra != rb:
            parent[rb] = ra
    for src, neighbors in graph.items():
        for dst in neighbors:
            union(src, dst)
    groups = {}
    for node in nodes:
        groups.setdefault(find(node), []).append(node)
    return sorted(sorted(group) for group in groups.values())
"""


GRAPH_TOPOLOGICAL_SORT_CODE = """
def solve(input_data):
    graph = input_data["graph"]
    indegree = {node: 0 for node in graph}
    for src, neighbors in graph.items():
        indegree.setdefault(src, 0)
        for dst in neighbors:
            indegree[dst] = indegree.get(dst, 0) + 1
    queue = sorted([node for node, degree in indegree.items() if degree == 0])
    order = []
    head = 0
    while head < len(queue):
        node = queue[head]
        head += 1
        order.append(node)
        for neighbor in graph.get(node, []):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)
    return order
"""


GRAPH_TOPOLOGICAL_SORT_TRACKER = """
def trace(input_data):
    graph = input_data["graph"]
    indegree = {node: 0 for node in graph}
    for src, neighbors in graph.items():
        indegree.setdefault(src, 0)
        for dst in neighbors:
            indegree[dst] = indegree.get(dst, 0) + 1
    queue = sorted([node for node, degree in indegree.items() if degree == 0])
    order = []
    head = 0
    contract = {"submode": "topological_sort", "expected_nodes": sorted(indegree)}
    tracer = Tracer(input_data, algorithm="拓扑排序", pseudocode=["入度为 0 的点入队", "弹出节点并删除出边", "邻居入度归零后入队"], policy="full", max_events=220)

    def state(current=None):
        return {"graph": graph, "queue": queue[head:], "indegree": dict(indegree), "topo_order": order[:], "current": current, "graph_contract": contract}

    tracer.create("queue", state=state(), reason="初始化所有入度为 0 的节点进入队列。", code_line=1)
    while head < len(queue):
        node = queue[head]
        head += 1
        order.append(node)
        tracer.pop("queue", value=node, deps=[f"node:{node}"], state=state(node), role="current", reason="弹出一个入度为 0 的节点，加入拓扑序。", code_line=8)
        for neighbor in graph.get(node, []):
            before = indegree[neighbor]
            indegree[neighbor] -= 1
            enqueue_reason = "入队：入度归零" if indegree[neighbor] == 0 else "尚未入队：仍有前置依赖"
            if indegree[neighbor] == 0:
                queue.append(neighbor)
            tracer.set(
                f"indegree[{neighbor}]",
                value=indegree[neighbor],
                before=before,
                after=indegree[neighbor],
                deps=[f"edge:{node}->{neighbor}"],
                state={**state(node), "enqueue_reason": enqueue_reason},
                role="current",
                reason=f"删除边 {node}->{neighbor} 后更新入度；{enqueue_reason}。",
                code_line=11,
            )
    tracer.mark("order", value=order[:], state=state(), role="answer", reason="拓扑排序完成。", code_line=14)
    tracer.result(order)
    return tracer.to_trace()
"""


GRAPH_TOPOLOGICAL_SORT_VERIFIER = """
def verify(input_data):
    graph = input_data["graph"]
    indegree = {}
    for node, neighbors in graph.items():
        indegree.setdefault(node, 0)
        for neighbor in neighbors:
            indegree[neighbor] = indegree.get(neighbor, 0) + 1
    remaining = dict(indegree)
    order = []
    while True:
        zero = sorted(node for node, degree in remaining.items() if degree == 0)
        if not zero:
            break
        node = zero[0]
        order.append(node)
        remaining.pop(node)
        for neighbor in graph.get(node, []):
            if neighbor in remaining:
                remaining[neighbor] -= 1
    return order
"""


GRAPH_BIPARTITE_COLORING_CODE = """
def solve(input_data):
    graph = input_data["graph"]
    color = {}
    for start in sorted(graph):
        if start in color:
            continue
        color[start] = 0
        queue = [start]
        head = 0
        while head < len(queue):
            node = queue[head]
            head += 1
            for neighbor in graph.get(node, []):
                if neighbor not in color:
                    color[neighbor] = 1 - color[node]
                    queue.append(neighbor)
    return color
"""


GRAPH_BIPARTITE_COLORING_TRACKER = """
def trace(input_data):
    graph = input_data["graph"]
    color = {}
    queue = []
    head = 0
    contract = {"submode": "bipartite_coloring", "expected_nodes": sorted(graph)}
    tracer = Tracer(input_data, algorithm="二分图染色", pseudocode=["未染色点作为新起点", "相邻节点染成相反颜色", "队列扩展整张图"], policy="full", max_events=220)

    def state(current=None, neighbor=None):
        return {"graph": graph, "queue": queue[head:], "color": dict(color), "current": current, "neighbor": neighbor, "graph_contract": contract}

    tracer.create("queue", state=state(), reason="初始化颜色映射，准备按连通块 BFS 染色。", code_line=1)
    for start in sorted(graph):
        if start in color:
            continue
        color[start] = 0
        queue.append(start)
        tracer.set("color[" + str(start) + "]", value=0, deps=[f"node:{start}"], state=state(start), role="current", reason="新的连通块起点染成颜色 0 并入队。", code_line=5)
        while head < len(queue):
            node = queue[head]
            head += 1
            tracer.pop("queue", value=node, deps=[f"node:{node}"], state=state(node), role="current", reason="弹出当前节点，检查所有相邻节点。", code_line=8)
            for neighbor in graph.get(node, []):
                tracer.compare([f"edge:{node}->{neighbor}", f"color[{node}]"], deps=[f"node:{node}"], state=state(node, neighbor), role="candidate", reason="相邻节点必须使用相反颜色。", code_line=10)
                if neighbor not in color:
                    color[neighbor] = 1 - color[node]
                    queue.append(neighbor)
                    tracer.set("color[" + str(neighbor) + "]", value=color[neighbor], deps=[f"color[{node}]", f"edge:{node}->{neighbor}"], state=state(node, neighbor), role="visited", reason="首次遇到邻居，将它染成与当前节点相反的颜色。", code_line=12)
    tracer.mark("color", value=dict(color), state=state(), role="answer", reason="所有可达节点完成二分图染色。", code_line=14)
    tracer.result(color)
    return tracer.to_trace()
"""


GRAPH_BIPARTITE_COLORING_VERIFIER = """
def verify(input_data):
    graph = input_data["graph"]
    color = {}
    for start in sorted(graph):
        if start in color:
            continue
        color[start] = 0
        frontier = [start]
        while frontier:
            nxt = []
            for node in frontier:
                for neighbor in graph.get(node, []):
                    if neighbor not in color:
                        color[neighbor] = 1 - color[node]
                        nxt.append(neighbor)
            frontier = nxt
    return color
"""


DIJKSTRA_SHORTEST_PATH_CODE = """
def solve(input_data):
    import heapq
    graph = input_data["weighted_graph"]
    start = input_data["start"]
    dist = {start: 0}
    parent = {}
    heap = [(0, start)]
    while heap:
        cur_dist, node = heapq.heappop(heap)
        if cur_dist != dist.get(node):
            continue
        for neighbor, weight in graph.get(node, []):
            candidate = cur_dist + weight
            if candidate < dist.get(neighbor, 10**9):
                dist[neighbor] = candidate
                parent[neighbor] = node
                heapq.heappush(heap, (candidate, neighbor))
    return dist
"""


DIJKSTRA_SHORTEST_PATH_TRACKER = """
def trace(input_data):
    import heapq
    weighted_graph = input_data["weighted_graph"]
    start = input_data["start"]
    graph = {node: [edge[0] for edge in edges] for node, edges in weighted_graph.items()}
    dist = {start: 0}
    parent = {}
    heap = [(0, start)]
    contract = {"submode": "dijkstra", "source": start, "expected_relax_edges": []}
    tracer = Tracer(input_data, algorithm="Dijkstra 最短路", pseudocode=["堆中取出当前最短节点", "用当前距离松弛出边"], policy="full", max_events=260)

    def state(current=None, neighbor=None, weight=None, old_dist=None, new_dist=None):
        return {
            "graph": graph,
            "weighted_graph": weighted_graph,
            "heap": [list(item) for item in heap],
            "dist": dict(dist),
            "parent": dict(parent),
            "current": current,
            "neighbor": neighbor,
            "weight": weight,
            "old_dist": old_dist,
            "new_dist": new_dist,
            "graph_contract": contract,
        }

    tracer.create("heap", state=state(start), reason="起点距离为 0，加入最小堆。", code_line=1)
    while heap:
        cur_dist, node = heapq.heappop(heap)
        tracer.pop("heap", value=[cur_dist, node], deps=[f"node:{node}"], state=state(node), role="current", reason="弹出当前堆顶节点，它拥有目前最小的候选距离。", code_line=5)
        if cur_dist != dist.get(node):
            continue
        for neighbor, weight in weighted_graph.get(node, []):
            tracer.compare([f"edge:{node}->{neighbor}", f"dist[{node}]", f"dist[{neighbor}]"], deps=[f"node:{node}"], state=state(node, neighbor, weight, dist.get(neighbor, 10**9), cur_dist + weight), role="candidate", reason="检查当前边是否能让邻居距离变短。", code_line=8)
            candidate = cur_dist + weight
            old = dist.get(neighbor, 10**9)
            if candidate < old:
                dist[neighbor] = candidate
                parent[neighbor] = node
                heapq.heappush(heap, (candidate, neighbor))
                contract["expected_relax_edges"].append(f"{node}->{neighbor}")
                tracer.set(f"dist[{neighbor}]", value=candidate, before=old, after=candidate, deps=[f"dist[{node}]", f"edge:{node}->{neighbor}"], state=state(node, neighbor, weight, old, candidate), role="current", reason="通过当前边完成 Dijkstra 松弛并更新父节点。", code_line=11)
    tracer.mark("dist", value=dict(dist), state=state(), role="answer", reason="堆为空，所有可达节点的最短距离已确定。", code_line=15)
    tracer.result(dist)
    return tracer.to_trace()
"""


DIJKSTRA_SHORTEST_PATH_VERIFIER = """
def verify(input_data):
    graph = input_data["weighted_graph"]
    start = input_data["start"]
    nodes = set(graph)
    for edges in graph.values():
        for node, _weight in edges:
            nodes.add(node)
    dist = {node: 10**9 for node in nodes}
    dist[start] = 0
    for _ in range(len(nodes) - 1):
        changed = False
        for src, edges in graph.items():
            if dist[src] >= 10**9:
                continue
            for dst, weight in edges:
                if dist[src] + weight < dist[dst]:
                    dist[dst] = dist[src] + weight
                    changed = True
        if not changed:
            break
    return {node: value for node, value in dist.items() if value < 10**9}
"""


BELLMAN_FORD_SHORTEST_PATH_CODE = """
def solve(input_data):
    edges = input_data["edges"]
    start = input_data["start"]
    nodes = set([start])
    for u, v, _w in edges:
        nodes.add(u)
        nodes.add(v)
    inf = 10**9
    dist = {node: inf for node in nodes}
    dist[start] = 0
    for _ in range(max(0, len(nodes) - 1)):
        changed = False
        for u, v, w in edges:
            if dist[u] == inf:
                continue
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changed = True
        if not changed:
            break
    return {node: value for node, value in dist.items() if value < inf}
"""


BELLMAN_FORD_SHORTEST_PATH_TRACKER = """
def trace(input_data):
    edges = input_data["edges"]
    start = input_data["start"]
    nodes = sorted({start} | {u for u, _v, _w in edges} | {v for _u, v, _w in edges})
    graph = {node: [] for node in nodes}
    for u, v, _w in edges:
        graph.setdefault(u, []).append(v)
        graph.setdefault(v, graph.get(v, []))
    inf = 10**9
    dist = {node: inf for node in nodes}
    dist[start] = 0
    contract = {"submode": "bellman_ford", "source": start, "expected_relax_edges": []}
    tracer = Tracer(input_data, algorithm="Bellman-Ford 最短路", pseudocode=["重复 V-1 轮扫描所有边", "如果 dist[u]+w 更小则松弛 dist[v]"], policy="full", max_events=260)

    def state(round_index=0, current_edge=None, old_dist=None, new_dist=None):
        return {"graph": graph, "edges": edges, "dist": dict(dist), "round": round_index, "current_edge": current_edge, "old_dist": old_dist, "new_dist": new_dist, "graph_contract": contract}

    tracer.create("dist", state=state(), reason="初始化起点距离为 0，其余节点为不可达大数。", code_line=1)
    for round_index in range(1, max(1, len(nodes))):
        changed = False
        for u, v, w in edges:
            tracer.compare([f"edge:{u}->{v}", f"dist[{u}]", f"dist[{v}]"], deps=[f"dist[{u}]"], state=state(round_index, [u, v, w], dist.get(v, inf), dist.get(u, inf) + w), role="candidate", reason="扫描当前边，判断是否可以松弛。", code_line=8)
            if dist.get(u, inf) == inf:
                continue
            candidate = dist[u] + w
            old = dist.get(v, inf)
            if candidate < old:
                dist[v] = candidate
                changed = True
                contract["expected_relax_edges"].append(f"{u}->{v}")
                tracer.set(f"dist[{v}]", value=candidate, before=old, after=candidate, deps=[f"dist[{u}]", f"edge:{u}->{v}"], state=state(round_index, [u, v, w], old, candidate), role="current", reason="Bellman-Ford 本轮扫描边并完成一次松弛。", code_line=12)
        if not changed:
            break
    answer = {node: value for node, value in dist.items() if value < inf}
    tracer.mark("dist", value=answer, state=state(), role="answer", reason="边扫描结束，返回所有可达节点距离。", code_line=15)
    tracer.result(answer)
    return tracer.to_trace()
"""


BELLMAN_FORD_SHORTEST_PATH_VERIFIER = """
def verify(input_data):
    edges = input_data["edges"]
    start = input_data["start"]
    nodes = sorted({start} | {edge[0] for edge in edges} | {edge[1] for edge in edges})
    inf = 10**9
    best = {node: inf for node in nodes}
    best[start] = 0
    for _ in nodes:
        updated = {}
        for u, v, w in edges:
            if best[u] < inf:
                candidate = best[u] + w
                if candidate < best[v]:
                    updated[v] = candidate
        if not updated:
            break
        best.update(updated)
    return {node: value for node, value in best.items() if value < inf}
"""


FLOYD_WARSHALL_ALL_PAIRS_CODE = """
def solve(input_data):
    dist = [row[:] for row in input_data["dist"]]
    n = len(dist)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                candidate = dist[i][k] + dist[k][j]
                if candidate < dist[i][j]:
                    dist[i][j] = candidate
    return dist
"""


FLOYD_WARSHALL_ALL_PAIRS_TRACKER = """
def trace(input_data):
    dist = [row[:] for row in input_data["dist"]]
    n = len(dist)
    graph = {str(i): [str(j) for j in range(n) if i != j and dist[i][j] < 10**8] for i in range(n)}
    contract = {"submode": "floyd_warshall", "expected_relax_edges": []}
    tracer = Tracer(input_data, algorithm="Floyd-Warshall 全源最短路", pseudocode=["枚举中转点 k", "dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])"], policy="full", max_events=260)

    def state(k=0, i=0, j=0):
        return {"graph": graph, "dist": [row[:] for row in dist], "k": k, "i": i, "j": j, "graph_contract": contract}

    tracer.create("dist", state=state(), reason="初始化全源距离矩阵。", code_line=1)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                tracer.compare([f"dist[{i}][{j}]", f"dist[{i}][{k}]", f"dist[{k}][{j}]"], deps=[f"dist[{i}][{k}]", f"dist[{k}][{j}]"], state=state(k, i, j), role="candidate", reason="尝试使用当前 k 作为中转点更新 i 到 j 的距离。", code_line=5)
                candidate = dist[i][k] + dist[k][j]
                if candidate < dist[i][j]:
                    old = dist[i][j]
                    dist[i][j] = candidate
                    contract["expected_relax_edges"].append(f"{i}->{j}")
                    tracer.set(f"dist[{i}][{j}]", value=candidate, before=old, after=candidate, deps=[f"dist[{i}][{k}]", f"dist[{k}][{j}]"], state=state(k, i, j), role="current", reason="Floyd 通过当前中转点得到更短路径。", code_line=7)
    tracer.mark("dist", value=[row[:] for row in dist], state=state(), role="answer", reason="所有中转点处理完毕，得到全源最短路。", code_line=8)
    tracer.result(dist)
    return tracer.to_trace()
"""


FLOYD_WARSHALL_ALL_PAIRS_VERIFIER = """
def verify(input_data):
    dist = [row[:] for row in input_data["dist"]]
    n = len(dist)
    for i in range(n):
        for j in range(n):
            for k in range(n):
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
    return dist
"""


ZERO_ONE_BFS_SHORTEST_PATH_CODE = """
def solve(input_data):
    from collections import deque
    graph = input_data["weighted_graph"]
    start = input_data["start"]
    dist = {start: 0}
    dq = deque([start])
    while dq:
        node = dq.popleft()
        for neighbor, weight in graph.get(node, []):
            candidate = dist[node] + weight
            if candidate < dist.get(neighbor, 10**9):
                dist[neighbor] = candidate
                if weight == 0:
                    dq.appendleft(neighbor)
                else:
                    dq.append(neighbor)
    return dist
"""


ZERO_ONE_BFS_SHORTEST_PATH_TRACKER = """
def trace(input_data):
    from collections import deque
    weighted_graph = input_data["weighted_graph"]
    start = input_data["start"]
    graph = {node: [edge[0] for edge in edges] for node, edges in weighted_graph.items()}
    dist = {start: 0}
    dq = deque([start])
    contract = {"submode": "zero_one_bfs", "source": start, "expected_relax_edges": []}
    tracer = Tracer(input_data, algorithm="0-1 BFS 最短路", pseudocode=["权重 0 的边放入队首", "权重 1 的边放入队尾"], policy="full", max_events=220)

    def state(current=None, neighbor=None, weight=None, old_dist=None, new_dist=None):
        return {"graph": graph, "weighted_graph": weighted_graph, "deque": list(dq), "dist": dict(dist), "current": current, "neighbor": neighbor, "weight": weight, "old_dist": old_dist, "new_dist": new_dist, "graph_contract": contract}

    tracer.create("deque", state=state(start), reason="起点进入双端队列，距离为 0。", code_line=1)
    while dq:
        node = dq.popleft()
        tracer.pop("deque", value=node, deps=[f"node:{node}"], state=state(node), role="current", reason="从双端队列头部取出当前节点。", code_line=5)
        for neighbor, weight in weighted_graph.get(node, []):
            candidate = dist[node] + weight
            old = dist.get(neighbor, 10**9)
            tracer.compare([f"edge:{node}->{neighbor}", f"dist[{neighbor}]"], deps=[f"dist[{node}]"], state=state(node, neighbor, weight, old, candidate), role="candidate", reason="检查 0/1 权重边是否能缩短距离。", code_line=7)
            if candidate < old:
                dist[neighbor] = candidate
                if weight == 0:
                    dq.appendleft(neighbor)
                else:
                    dq.append(neighbor)
                contract["expected_relax_edges"].append(f"{node}->{neighbor}")
                tracer.set(f"dist[{neighbor}]", value=candidate, before=old, after=candidate, deps=[f"dist[{node}]", f"edge:{node}->{neighbor}"], state=state(node, neighbor, weight, old, candidate), role="current", reason="按边权选择队首或队尾入队并更新最短距离。", code_line=10)
    tracer.mark("dist", value=dict(dist), state=state(), role="answer", reason="双端队列为空，返回 0-1 BFS 距离。", code_line=14)
    tracer.result(dist)
    return tracer.to_trace()
"""


ZERO_ONE_BFS_SHORTEST_PATH_VERIFIER = """
def verify(input_data):
    graph = input_data["weighted_graph"]
    start = input_data["start"]
    nodes = set([start])
    for src, edges in graph.items():
        nodes.add(src)
        for dst, _w in edges:
            nodes.add(dst)
    dist = {node: 10**9 for node in nodes}
    dist[start] = 0
    for _ in nodes:
        changed = False
        for src, edges in graph.items():
            if dist[src] >= 10**9:
                continue
            for dst, weight in edges:
                if dist[src] + weight < dist[dst]:
                    dist[dst] = dist[src] + weight
                    changed = True
        if not changed:
            break
    return {node: value for node, value in dist.items() if value < 10**9}
"""


KRUSKAL_MST_WEIGHT_CODE = """
def solve(input_data):
    edges = input_data["edges"]
    nodes = sorted({u for u, _v, _w in edges} | {v for _u, v, _w in edges})
    parent = {node: node for node in nodes}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    total = 0
    for u, v, w in sorted(edges, key=lambda item: (item[2], item[0], item[1])):
        ru, rv = find(u), find(v)
        if ru == rv:
            continue
        parent[rv] = ru
        total += w
    return total
"""


KRUSKAL_MST_WEIGHT_TRACKER = """
def trace(input_data):
    edges = input_data["edges"]
    nodes = sorted({u for u, _v, _w in edges} | {v for _u, v, _w in edges})
    graph = {node: [] for node in nodes}
    for u, v, _w in edges:
        graph[u].append(v)
        graph[v].append(u)
    parent = {node: node for node in nodes}
    rank = {node: 0 for node in nodes}
    mst_edges = []
    total = 0
    contract = {"submode": "mst", "expected_edges": []}
    tracer = Tracer(input_data, algorithm="Kruskal 最小生成树", pseudocode=["按权重从小到大考虑边", "若两端不连通则选择该边并 union"], policy="full", max_events=220)

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    def uf_state():
        return {"parent": dict(parent), "rank": dict(rank)}

    def state(edge=None, decision=None, reason_text=""):
        return {"graph": graph, "edges": edges, "union_find": uf_state(), "mst_edges": [item[:] for item in mst_edges], "current_edge": edge, "edge_decision": decision, "decision_reason": reason_text, "graph_contract": contract}

    tracer.create("union_find", state=state(), reason="初始化每个节点为单独集合。", code_line=1)
    for u, v, w in sorted(edges, key=lambda item: (item[2], item[0], item[1])):
        ru, rv = find(u), find(v)
        tracer.compare([f"edge:{u}->{v}", f"node:{u}", f"node:{v}"], state=state([u, v, w], "candidate", "比较边两端集合"), role="candidate", reason="检查当前最小候选边是否连接两个不同连通块。", code_line=8)
        if ru == rv:
            tracer.mark(f"edge:{u}->{v}", value="rejected", deps=[f"node:{u}", f"node:{v}"], state=state([u, v, w], "rejected", "两端已连通，选择会形成环"), role="rejected", reason="两端已经在同一集合，跳过该边避免形成环。", code_line=10)
            continue
        if rank[ru] < rank[rv]:
            ru, rv = rv, ru
        parent[rv] = ru
        if rank[ru] == rank[rv]:
            rank[ru] += 1
        mst_edges.append([u, v, w])
        total += w
        contract["expected_edges"].append(f"{u}-{v}")
        tracer.mark(f"edge:{u}->{v}", value=total, deps=[f"node:{u}", f"node:{v}"], state=state([u, v, w], "selected", "两端不连通，选择该边并合并集合"), role="selected", reason="选择当前边并执行 union，MST 总权重增加。", code_line=12)
    tracer.mark("mst_edges", value=total, state=state(), role="answer", reason="所有候选边处理完毕，得到最小生成树权重。", code_line=15)
    tracer.result(total)
    return tracer.to_trace()
"""


KRUSKAL_MST_WEIGHT_VERIFIER = """
def verify(input_data):
    edges = input_data["edges"]
    nodes = sorted(set([node for edge in edges for node in edge[:2]]))
    best = None
    from itertools import combinations
    for subset in combinations(edges, max(0, len(nodes) - 1)):
        parent = {node: node for node in nodes}
        def find(x):
            while parent[x] != x:
                x = parent[x]
            return x
        ok = True
        total = 0
        for u, v, w in subset:
            ru, rv = find(u), find(v)
            if ru == rv:
                ok = False
                break
            parent[rv] = ru
            total += w
        if ok and len({find(node) for node in nodes}) == 1:
            best = total if best is None else min(best, total)
    return 0 if best is None else best
"""


def cases() -> tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase(
            id="graph_bfs",
            title="图 BFS 最短层数",
            problem=(
                "给定一个无权图的邻接表 graph 和起点 start，"
                "返回从 start 到所有可达节点的最短边数距离。"
            ),
            family="BFS/DFS 基础图",
            input_contract="输入邻接表 graph 和起点 start。",
            variant_name="队列 BFS",
            strategy="队列按层扩展，首次访问时确定距离。",
            time_complexity="O(V+E)",
            space_complexity="O(V)",
            expected_layouts=("graph", "queue"),
            code=GRAPH_BFS_CODE,
            tracker_code=GRAPH_BFS_TRACKER,
            verifier_code=GRAPH_BFS_VERIFIER,
            samples=(
                BenchmarkInput({"graph": {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}, "start": "A"}, {"A": 0, "B": 1, "C": 1, "D": 2}),
                BenchmarkInput({"graph": {"1": ["2"], "2": ["3"], "3": [], "4": []}, "start": "1"}, {"1": 0, "2": 1, "3": 2}),
            ),
        ),
        BenchmarkCase(
            id="graph_dfs_traversal",
            title="图 DFS 遍历",
            problem="给定无权图邻接表 graph 和起点 start，使用递归 DFS 返回首次访问顺序。",
            family="BFS/DFS 基础图",
            input_contract="输入邻接表 graph 和起点 start。",
            variant_name="递归 DFS",
            strategy="进入递归帧时标记访问，按邻接表顺序深度优先探索未访问邻居。",
            time_complexity="O(V+E)",
            space_complexity="O(V)",
            expected_layouts=("graph", "stack"),
            code=GRAPH_DFS_TRAVERSAL_CODE,
            tracker_code=GRAPH_DFS_TRAVERSAL_TRACKER,
            verifier_code=GRAPH_DFS_TRAVERSAL_VERIFIER,
            samples=(
                BenchmarkInput({"graph": {"A": ["B", "C"], "B": ["D"], "C": [], "D": []}, "start": "A"}, ["A", "B", "D", "C"]),
                BenchmarkInput({"graph": {"1": ["2"], "2": ["3"], "3": [], "4": []}, "start": "1"}, ["1", "2", "3"]),
                BenchmarkInput({"graph": {"S": ["A", "B"], "A": ["C"], "B": ["C"], "C": []}, "start": "S"}, ["S", "A", "C", "B"]),
                BenchmarkInput({"graph": {"X": []}, "start": "X"}, ["X"]),
                BenchmarkInput({"graph": {"0": ["1"], "1": ["0", "2"], "2": []}, "start": "0"}, ["0", "1", "2"]),
            ),
        ),
        BenchmarkCase(
            id="graph_connected_components",
            title="图连通分量",
            problem="给定无向图邻接表 graph，返回所有连通分量，每个分量内节点按字典序排列。",
            family="BFS/DFS 基础图",
            input_contract="输入无向图邻接表 graph。",
            variant_name="DFS 收集连通分量",
            strategy="从每个未访问节点开始 DFS，把同一连通块中的节点收集成一个分量。",
            time_complexity="O(V+E)",
            space_complexity="O(V)",
            expected_layouts=("graph", "map"),
            code=GRAPH_CONNECTED_COMPONENTS_CODE,
            tracker_code=GRAPH_CONNECTED_COMPONENTS_TRACKER,
            verifier_code=GRAPH_CONNECTED_COMPONENTS_VERIFIER,
            samples=(
                BenchmarkInput({"graph": {"A": ["B"], "B": ["A"], "C": []}}, [["A", "B"], ["C"]]),
                BenchmarkInput({"graph": {"1": ["2"], "2": ["1", "3"], "3": ["2"], "4": ["5"], "5": ["4"]}}, [["1", "2", "3"], ["4", "5"]]),
                BenchmarkInput({"graph": {"X": []}}, [["X"]]),
                BenchmarkInput({"graph": {"A": ["B", "C"], "B": ["A"], "C": ["A"], "D": []}}, [["A", "B", "C"], ["D"]]),
                BenchmarkInput({"graph": {"0": ["1"], "1": ["0"], "2": [], "3": ["4"], "4": ["3"]}}, [["0", "1"], ["2"], ["3", "4"]]),
            ),
        ),
        BenchmarkCase(
            id="graph_topological_sort",
            title="拓扑排序",
            problem="给定有向无环图 graph，返回一个合法拓扑序。",
            family="BFS/DFS 基础图",
            input_contract="输入 DAG 邻接表 graph。",
            variant_name="Kahn 入度队列",
            strategy="维护入度表和零入度队列，每弹出一个节点就删除它的出边。",
            time_complexity="O(V+E)",
            space_complexity="O(V)",
            expected_layouts=("graph", "queue", "map"),
            code=GRAPH_TOPOLOGICAL_SORT_CODE,
            tracker_code=GRAPH_TOPOLOGICAL_SORT_TRACKER,
            verifier_code=GRAPH_TOPOLOGICAL_SORT_VERIFIER,
            samples=(
                BenchmarkInput({"graph": {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}}, ["A", "B", "C", "D"]),
                BenchmarkInput({"graph": {"1": ["3"], "2": ["3"], "3": []}}, ["1", "2", "3"]),
                BenchmarkInput({"graph": {"S": ["A"], "A": ["B"], "B": []}}, ["S", "A", "B"]),
                BenchmarkInput({"graph": {"X": []}}, ["X"]),
                BenchmarkInput({"graph": {"0": ["1", "2"], "1": ["3"], "2": ["3"], "3": ["4"], "4": []}}, ["0", "1", "2", "3", "4"]),
            ),
        ),
        BenchmarkCase(
            id="graph_bipartite_coloring",
            title="二分图染色",
            problem="给定无向二分图 graph，使用 BFS 染色返回每个节点的 0/1 颜色。",
            family="BFS/DFS 基础图",
            input_contract="输入无向二分图邻接表 graph。",
            variant_name="BFS 二分图染色",
            strategy="每个未染色连通块从颜色 0 开始，相邻节点染成相反颜色。",
            time_complexity="O(V+E)",
            space_complexity="O(V)",
            expected_layouts=("graph", "queue", "map"),
            code=GRAPH_BIPARTITE_COLORING_CODE,
            tracker_code=GRAPH_BIPARTITE_COLORING_TRACKER,
            verifier_code=GRAPH_BIPARTITE_COLORING_VERIFIER,
            samples=(
                BenchmarkInput({"graph": {"A": ["B", "D"], "B": ["A", "C"], "C": ["B", "D"], "D": ["A", "C"]}}, {"A": 0, "B": 1, "D": 1, "C": 0}),
                BenchmarkInput({"graph": {"1": ["2"], "2": ["1", "3"], "3": ["2"]}}, {"1": 0, "2": 1, "3": 0}),
                BenchmarkInput({"graph": {"X": []}}, {"X": 0}),
                BenchmarkInput({"graph": {"L1": ["R1", "R2"], "L2": ["R2"], "R1": ["L1"], "R2": ["L1", "L2"]}}, {"L1": 0, "R1": 1, "R2": 1, "L2": 0}),
                BenchmarkInput({"graph": {"A": ["B"], "B": ["A"], "C": ["D"], "D": ["C"]}}, {"A": 0, "B": 1, "C": 0, "D": 1}),
            ),
        ),
        BenchmarkCase(
            id="dijkstra_shortest_path",
            title="Dijkstra 最短路",
            problem=(
                "城市应急调度中心维护一张非负耗时的有向道路网 weighted_graph，"
                "每个节点表示路口，每条边权表示从一个路口到另一个路口的通行时间。"
                "给定救援车辆出发路口 start，返回它到所有可达路口的最短通行时间。"
            ),
            family="最短路 / MST",
            input_contract="输入 weighted_graph 邻接表和 start。",
            variant_name="堆优化 Dijkstra",
            strategy="最小堆按当前候选距离弹出节点，用非负权边松弛邻居。",
            time_complexity="O((V+E) log V)",
            space_complexity="O(V)",
            expected_layouts=("graph", "heap", "map"),
            code=DIJKSTRA_SHORTEST_PATH_CODE,
            tracker_code=DIJKSTRA_SHORTEST_PATH_TRACKER,
            verifier_code=DIJKSTRA_SHORTEST_PATH_VERIFIER,
            samples=(
                BenchmarkInput({"weighted_graph": {"A": [["B", 2], ["C", 5]], "B": [["C", 1]], "C": []}, "start": "A"}, {"A": 0, "B": 2, "C": 3}),
                BenchmarkInput({"weighted_graph": {"S": [["A", 1], ["B", 4]], "A": [["B", 2], ["T", 6]], "B": [["T", 1]], "T": []}, "start": "S"}, {"S": 0, "A": 1, "B": 3, "T": 4}),
                BenchmarkInput({"weighted_graph": {"1": [["2", 3]], "2": [], "3": []}, "start": "1"}, {"1": 0, "2": 3}),
                BenchmarkInput({"weighted_graph": {"X": []}, "start": "X"}, {"X": 0}),
            ),
        ),
        BenchmarkCase(
            id="bellman_ford_shortest_path",
            title="Bellman-Ford 最短路",
            problem="给定带权有向边列表 edges 和起点 start，返回所有可达点最短距离。",
            family="最短路 / MST",
            input_contract="输入 edges=[u,v,w] 和 start。",
            variant_name="Bellman-Ford 边松弛",
            strategy="最多 V-1 轮扫描所有边，允许负权边但不包含负环。",
            time_complexity="O(VE)",
            space_complexity="O(V)",
            expected_layouts=("graph", "map"),
            code=BELLMAN_FORD_SHORTEST_PATH_CODE,
            tracker_code=BELLMAN_FORD_SHORTEST_PATH_TRACKER,
            verifier_code=BELLMAN_FORD_SHORTEST_PATH_VERIFIER,
            samples=(
                BenchmarkInput({"edges": [["A", "B", 4], ["A", "C", 5], ["B", "C", -2]], "start": "A"}, {"A": 0, "B": 4, "C": 2}),
                BenchmarkInput({"edges": [["S", "A", 1], ["S", "B", 4], ["A", "B", -1], ["B", "T", 2]], "start": "S"}, {"S": 0, "A": 1, "B": 0, "T": 2}),
                BenchmarkInput({"edges": [["1", "2", 3], ["3", "4", -5]], "start": "1"}, {"1": 0, "2": 3}),
                BenchmarkInput({"edges": [["X", "Y", 0]], "start": "X"}, {"X": 0, "Y": 0}),
            ),
        ),
        BenchmarkCase(
            id="floyd_warshall_all_pairs",
            title="Floyd-Warshall 全源最短路",
            problem="给定距离矩阵 dist，使用 Floyd-Warshall 返回所有点对最短距离。",
            family="最短路 / MST",
            input_contract="输入 dist 方阵，使用 100000000 表示不可达。",
            variant_name="Floyd 中转点 DP",
            strategy="按 k 阶段枚举中转点，更新任意 i 到 j 的距离。",
            time_complexity="O(n^3)",
            space_complexity="O(n^2)",
            expected_layouts=("matrix", "graph"),
            code=FLOYD_WARSHALL_ALL_PAIRS_CODE,
            tracker_code=FLOYD_WARSHALL_ALL_PAIRS_TRACKER,
            verifier_code=FLOYD_WARSHALL_ALL_PAIRS_VERIFIER,
            samples=(
                BenchmarkInput({"dist": [[0, 2, 9], [2, 0, 3], [9, 3, 0]]}, [[0, 2, 5], [2, 0, 3], [5, 3, 0]]),
                BenchmarkInput({"dist": [[0, 1, 100000000], [100000000, 0, 2], [4, 100000000, 0]]}, [[0, 1, 3], [6, 0, 2], [4, 5, 0]]),
                BenchmarkInput({"dist": [[0, 7], [7, 0]]}, [[0, 7], [7, 0]]),
                BenchmarkInput({"dist": [[0, 5, 1], [5, 0, 1], [1, 1, 0]]}, [[0, 2, 1], [2, 0, 1], [1, 1, 0]]),
            ),
        ),
        BenchmarkCase(
            id="zero_one_bfs_shortest_path",
            title="0-1 BFS 最短路",
            problem="给定边权只为 0 或 1 的有向图 weighted_graph 和起点 start，返回最短距离。",
            family="最短路 / MST",
            input_contract="输入 0/1 weighted_graph 和 start。",
            variant_name="双端队列 0-1 BFS",
            strategy="权重 0 的松弛节点进入队首，权重 1 的松弛节点进入队尾。",
            time_complexity="O(V+E)",
            space_complexity="O(V)",
            expected_layouts=("graph", "deque", "map"),
            code=ZERO_ONE_BFS_SHORTEST_PATH_CODE,
            tracker_code=ZERO_ONE_BFS_SHORTEST_PATH_TRACKER,
            verifier_code=ZERO_ONE_BFS_SHORTEST_PATH_VERIFIER,
            samples=(
                BenchmarkInput({"weighted_graph": {"A": [["B", 0], ["C", 1]], "B": [["C", 0]], "C": []}, "start": "A"}, {"A": 0, "B": 0, "C": 0}),
                BenchmarkInput({"weighted_graph": {"S": [["A", 1], ["B", 0]], "A": [["T", 0]], "B": [["A", 0], ["T", 1]], "T": []}, "start": "S"}, {"S": 0, "B": 0, "A": 0, "T": 0}),
                BenchmarkInput({"weighted_graph": {"1": [["2", 1]], "2": [], "3": []}, "start": "1"}, {"1": 0, "2": 1}),
            ),
        ),
        BenchmarkCase(
            id="kruskal_mst_weight",
            title="Kruskal 最小生成树",
            problem="给定无向带权边列表 edges，使用 Kruskal 返回最小生成树总权重。",
            family="最短路 / MST",
            input_contract="输入 edges=[u,v,w]。",
            variant_name="Kruskal + 并查集",
            strategy="按权重排序边，只有连接不同集合的边才加入 MST。",
            time_complexity="O(E log E)",
            space_complexity="O(V)",
            expected_layouts=("graph", "union_find"),
            code=KRUSKAL_MST_WEIGHT_CODE,
            tracker_code=KRUSKAL_MST_WEIGHT_TRACKER,
            verifier_code=KRUSKAL_MST_WEIGHT_VERIFIER,
            samples=(
                BenchmarkInput({"edges": [["A", "B", 1], ["B", "C", 2], ["A", "C", 3]]}, 3),
                BenchmarkInput({"edges": [["A", "B", 1], ["B", "C", 1], ["C", "D", 2], ["A", "D", 4], ["B", "D", 3]]}, 4),
                BenchmarkInput({"edges": [["X", "Y", 5]]}, 5),
            ),
        ),
    )
