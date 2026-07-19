
// Fixed problem input
export const initialTree = {
  nodes: [
    { id: "1", value: 3 },
    { id: "2", value: 2 },
    { id: "3", value: 1 },
    { id: "4", value: 10 },
    { id: "5", value: 1 },
  ],
  edges: [
    ["1", "2"],
    ["1", "3"],
    ["2", "4"],
    ["2", "5"],
  ],
};

// Build adjacency, values, parent map, children list
export function buildTree(nodes, edges) {
  const adj = {};
  nodes.forEach(n => adj[n.id] = []);
  edges.forEach(([u, v]) => {
    adj[u].push(v);
    adj[v].push(u);
  });
  const values = {};
  nodes.forEach(n => values[n.id] = n.value);
  const root = "1"; // fixed root
  const parent = {};
  const children = {};
  nodes.forEach(n => children[n.id] = []);
  const visited = new Set();

  function dfs(u, p) {
    visited.add(u);
    parent[u] = p;
    for (let v of adj[u]) {
      if (v !== p && !visited.has(v)) {
        children[u].push(v);
        dfs(v, u);
      }
    }
  }
  dfs(root, null);
  return { root, values, children, parent, adj };
}

// Postorder traversal
export function getPostorder(root, children) {
  const order = [];
  function dfs(u) {
    for (let v of children[u]) {
      dfs(v);
    }
    order.push(u);
  }
  dfs(root);
  return order;
}

// Compute correct DP values using the algorithm
export function computeCorrectDP(nodes, edges) {
  const { root, values, children } = buildTree(nodes, edges);
  const order = getPostorder(root, children);
  const dp_take = {};
  const dp_skip = {};

  for (let u of order) {
    let takeSum = 0;
    let skipSum = 0;
    for (let v of children[u]) {
      takeSum += dp_skip[v];
      skipSum += Math.max(dp_take[v], dp_skip[v]);
    }
    dp_take[u] = values[u] + takeSum;
    dp_skip[u] = skipSum;
  }

  return { dp_take, dp_skip, order, root, values, children };
}

// Generate initial trace steps
export function generateInitialSteps(nodes, edges) {
  const { root, values, children } = buildTree(nodes, edges);
  const order = getPostorder(root, children);
  const { dp_take: correctTake, dp_skip: correctSkip } = computeCorrectDP(nodes, edges);

  const steps = [];
  // Start step
  steps.push({
    type: 'start',
    nodeId: null,
    completed: true,
  });

  // Process each node in postorder
  const computedTake = {};
  const computedSkip = {};

  for (let u of order) {
    const childs = children[u];
    const childInfo = childs.map(v => ({
      id: v,
      dp_take: computedTake[v],
      dp_skip: computedSkip[v],
    }));

    // Leaf nodes don't require prediction (dp_take = value, dp_skip = 0)
    const requiresPrediction = childs.length > 0;

    steps.push({
      type: 'process',
      nodeId: u,
      value: values[u],
      children: childInfo,
      requiresPrediction,
      correctTake: correctTake[u],
      correctSkip: correctSkip[u],
      userTake: null,
      userSkip: null,
      solved: false,
      showAnswerUsed: false,
      completed: false,
    });

    // Pre-fill computed for subsequent nodes in the trace
    computedTake[u] = correctTake[u];
    computedSkip[u] = correctSkip[u];
  }

  return { steps, root, children, order, values };
}

// Compute tree layout for visualization
export function computeLayout(root, children) {
  let leafIndex = 0;
  const positions = {};

  function dfs(u, depth) {
    if (children[u].length === 0) {
      positions[u] = { x: leafIndex, y: depth };
      leafIndex++;
    } else {
      for (let v of children[u]) {
        dfs(v, depth + 1);
      }
      const childX = children[u].map(v => positions[v].x);
      const avgX = childX.reduce((a, b) => a + b, 0) / childX.length;
      positions[u] = { x: avgX, y: depth };
    }
  }
  dfs(root, 0);

  // Scale and offset
  const scaleX = 90;
  const scaleY = 80;
  const offsetX = 50;
  const offsetY = 50;

  const layout = {};
  for (let id in positions) {
    layout[id] = {
      x: positions[id].x * scaleX + offsetX,
      y: positions[id].y * scaleY + offsetY,
    };
  }
  return layout;
}
  