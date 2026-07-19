/**
 * Tarjan's algorithm for finding articulation points and bridges.
 * Returns the full step-by-step trace for educational visualization.
 */

export function runTarjan(graph) {
  const nodes = Object.keys(graph);
  const dfn = {};
  const low = {};
  const parent = {};
  const visited = new Set();
  let time = 0;
  const articulation = new Set();
  const bridges = [];
  const steps = [];

  function addStep(type, details) {
    steps.push({ type, ...details, stepNum: steps.length + 1 });
  }

  function dfs(u) {
    visited.add(u);
    time++;
    dfn[u] = time;
    low[u] = time;
    let children = 0;

    addStep('enter', {
      node: u,
      dfn: { ...dfn },
      low: { ...low },
      parent: { ...parent },
      visited: new Set(visited),
      time,
      description: `进入节点 ${u}，设置 dfn[${u}]=${dfn[u]}, low[${u}]=${low[u]}`
    });

    const neighbors = graph[u] || [];
    for (const v of neighbors) {
      if (!visited.has(v)) {
        children++;
        parent[v] = u;

        addStep('explore', {
          from: u,
          to: v,
          dfn: { ...dfn },
          low: { ...low },
          parent: { ...parent },
          visited: new Set(visited),
          time,
          description: `从 ${u} 探索未访问的邻居 ${v}，设置 parent[${v}]=${u}`
        });

        dfs(v);

        // After returning from child
        low[u] = Math.min(low[u], low[v]);

        addStep('backtrack', {
          from: v,
          to: u,
          dfn: { ...dfn },
          low: { ...low },
          parent: { ...parent },
          visited: new Set(visited),
          time,
          description: `回溯：从 ${v} 返回到 ${u}，low[${u}] = min(low[${u}], low[${v}]) = ${low[u]}`
        });

        // Check articulation point
        if (parent[u] !== undefined && low[v] >= dfn[u]) {
          articulation.add(u);
          addStep('articulation-found', {
            node: u,
            child: v,
            reason: `low[${v}]=${low[v]} >= dfn[${u}]=${dfn[u]}`,
            dfn: { ...dfn },
            low: { ...low },
            parent: { ...parent },
            visited: new Set(visited),
            time,
            description: `发现割点 ${u}：low[${v}]=${low[v]} >= dfn[${u}]=${dfn[u]}`
          });
        }

        // Check bridge
        if (low[v] > dfn[u]) {
          bridges.push([u, v]);
          addStep('bridge-found', {
            edge: [u, v],
            reason: `low[${v}]=${low[v]} > dfn[${u}]=${dfn[u]}`,
            dfn: { ...dfn },
            low: { ...low },
            parent: { ...parent },
            visited: new Set(visited),
            time,
            description: `发现桥 (${u}, ${v})：low[${v}]=${low[v]} > dfn[${u}]=${dfn[u]}`
          });
        }
      } else if (v !== parent[u]) {
        // Back edge
        low[u] = Math.min(low[u], dfn[v]);
        addStep('back-edge', {
          from: u,
          to: v,
          dfn: { ...dfn },
          low: { ...low },
          parent: { ...parent },
          visited: new Set(visited),
          time,
          description: `发现回边 (${u}, ${v})，low[${u}] = min(low[${u}], dfn[${v}]) = ${low[u]}`
        });
      }
    }

    // Check root articulation
    if (parent[u] === undefined && children > 1) {
      articulation.add(u);
      addStep('root-articulation', {
        node: u,
        children,
        dfn: { ...dfn },
        low: { ...low },
        parent: { ...parent },
        visited: new Set(visited),
        time,
        description: `根节点 ${u} 有 ${children} 个子节点 > 1，是割点`
      });
    }

    addStep('exit', {
      node: u,
      dfn: { ...dfn },
      low: { ...low },
      parent: { ...parent },
      visited: new Set(visited),
      time,
      description: `离开节点 ${u}`
    });
  }

  // Start DFS from first node
  for (const node of nodes) {
    if (!visited.has(node)) {
      addStep('start-component', {
        node,
        dfn: { ...dfn },
        low: { ...low },
        parent: { ...parent },
        visited: new Set(visited),
        time,
        description: `开始新的连通分量，从节点 ${node} 开始 DFS`
      });
      dfs(node);
    }
  }

  addStep('complete', {
    dfn: { ...dfn },
    low: { ...low },
    articulation: [...articulation].sort(),
    bridges: bridges.map(([u, v]) => [u, v].sort()).sort(),
    description: `算法完成。割点: [${[...articulation].sort().join(', ')}]，桥: [${bridges.map(([u, v]) => `(${u},${v})`).join(', ')}]`
  });

  return {
    articulation: [...articulation].sort(),
    bridges: bridges.map(([u, v]) => [u, v].sort()).sort((a, b) => a[0].localeCompare(b[0]) || a[1].localeCompare(b[1])),
    steps,
    dfn,
    low,
    parent
  };
}

export const PROBLEM_INPUT = {
  graph: {
    "A": ["B"],
    "B": ["A", "C", "D"],
    "C": ["B", "D"],
    "D": ["B", "C", "E"],
    "E": ["D"]
  }
};

export const EXPECTED_OUTPUT = {
  articulation: ["B", "D"],
  bridges: [["D", "E"], ["A", "B"]].sort((a, b) => a[0].localeCompare(b[0]) || a[1].localeCompare(b[1]))
};

// Graph node positions for visualization
export const NODE_POSITIONS = {
  A: { x: 150, y: 80 },
  B: { x: 250, y: 180 },
  C: { x: 400, y: 100 },
  D: { x: 400, y: 250 },
  E: { x: 530, y: 250 }
};

// Learner questions
export const QUIZ_QUESTIONS = [
  {
    id: 1,
    question: "当前 DFS 访问了节点 B，其 dfn[B]=2, low[B]=2，邻居有 C 和 D。下一步会访问哪个节点？为什么？",
    options: [
      { label: "A", text: "节点 A（父节点）", correct: false },
      { label: "B", text: "节点 C（按邻接表顺序优先）", correct: true },
      { label: "C", text: "节点 D（随机选择）", correct: false },
      { label: "D", text: "回溯到之前的节点", correct: false }
    ],
    explanation: "DFS 优先访问未访问的邻居。按邻接表顺序，C 在 D 之前，且 C 未被访问（A 是父节点会被跳过），因此下一步访问 C。"
  },
  {
    id: 2,
    question: "在执行 DFS 的过程中，dfn[u] 和 low[u] 之间的关系有什么不变性？",
    options: [
      { label: "A", text: "low[u] > dfn[u] 始终成立", correct: false },
      { label: "B", text: "low[u] <= dfn[u] 始终成立", correct: true },
      { label: "C", text: "low[u] == dfn[u] 始终成立", correct: false },
      { label: "D", text: "low[u] >= dfn[u] 始终成立", correct: false }
    ],
    explanation: "low[u] 表示从 u 出发能到达的最早 dfn。它要么等于自身的 dfn[u]，要么因回边/子树更新变得更小。因此 low[u] <= dfn[u] 始终成立。"
  },
  {
    id: 3,
    question: "若在原图 graph 中添加一条边 (C,E)，原来的桥 (D,E) 还会是桥吗？",
    options: [
      { label: "A", text: "仍然是桥", correct: false },
      { label: "B", text: "不再是桥，因为形成了环提供替代路径", correct: true },
      { label: "C", text: "D 变成割点", correct: false },
      { label: "D", text: "无法确定", correct: false }
    ],
    explanation: "添加 (C,E) 后，E 可以通过 C-B-D 路径返回，low[E] 将变小。D-E 不再是唯一的连接，因此 (D,E) 不再是桥。"
  },
  {
    id: 4,
    question: "回溯到节点 B 时，low[B] 从 2 更新为 1，请问这是由哪个子节点导致的？并解释更新原因。",
    options: [
      { label: "A", text: "子节点 C，因为 C 有回边到 A", correct: false },
      { label: "B", text: "子节点 A，因为 A 的 dfn 是 1", correct: true },
      { label: "C", text: "子节点 D，因为 D 连接了 E", correct: false },
      { label: "D", text: "自身更新导致", correct: false }
    ],
    explanation: "从 A 回溯到 B 时，low[A]=1，执行 low[B] = min(low[B], low[A]) = min(2, 1) = 1。这是因为子节点 A 的 low 值为 1（A 自身的 dfn）。"
  }
];