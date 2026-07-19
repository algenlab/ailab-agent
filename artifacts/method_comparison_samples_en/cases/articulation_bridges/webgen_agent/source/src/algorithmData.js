// Graph data and precomputed algorithm steps for Articulation Points and Bridges

export const graphData = {
  nodes: {
    A: { x: 120, y: 80 },
    B: { x: 270, y: 80 },
    C: { x: 420, y: 80 },
    D: { x: 270, y: 230 },
    E: { x: 420, y: 230 },
  },
  edges: [
    ['A', 'B'],
    ['B', 'C'],
    ['B', 'D'],
    ['C', 'D'],
    ['D', 'E'],
  ],
  adjacency: {
    A: ['B'],
    B: ['A', 'C', 'D'],
    C: ['B', 'D'],
    D: ['B', 'C', 'E'],
    E: ['D'],
  },
};

export const graphDataModified = {
  nodes: {
    A: { x: 120, y: 80 },
    B: { x: 270, y: 80 },
    C: { x: 420, y: 80 },
    D: { x: 270, y: 230 },
    E: { x: 420, y: 230 },
  },
  edges: [
    ['A', 'B'],
    ['B', 'C'],
    ['B', 'D'],
    ['C', 'D'],
    ['D', 'E'],
    ['C', 'E'],
  ],
  adjacency: {
    A: ['B'],
    B: ['A', 'C', 'D'],
    C: ['B', 'D', 'E'],
    D: ['B', 'C', 'E'],
    E: ['D', 'C'],
  },
};

// Build DFS steps for the original graph
function buildOriginalSteps() {
  const steps = [];
  let time = 0;
  const dfn = {};
  const low = {};
  const parent = {};
  const articulations = [];
  const bridges = [];
  const visited = new Set();

  function addStep(type, node, extra = {}) {
    steps.push({
      type,
      node,
      dfn: { ...dfn },
      low: { ...low },
      parent: { ...parent },
      articulations: [...articulations],
      bridges: bridges.map((b) => [...b]),
      visited: new Set(visited),
      ...extra,
    });
  }

  function dfs(u, p) {
    visited.add(u);
    time++;
    dfn[u] = time;
    low[u] = time;
    parent[u] = p;
    let children = 0;

    addStep('visit', u, {
      description: `Visit node ${u}: dfn[${u}]=${dfn[u]}, low[${u}]=${low[u]}, parent[${u}]=${p || 'null'}`,
      highlightNode: u,
      newDfn: u,
    });

    const neighbors = graphData.adjacency[u];
    for (const v of neighbors) {
      if (!visited.has(v)) {
        children++;
        addStep('explore', u, {
          neighbor: v,
          description: `Explore edge ${u}→${v}: ${v} is unvisited. Recursively call DFS(${v}).`,
          highlightEdge: [u, v],
          highlightNode: u,
        });

        dfs(v, u);

        // Backtrack: update low[u]
        const oldLow = low[u];
        low[u] = Math.min(low[u], low[v]);
        const lowChanged = oldLow !== low[u];

        let desc = `Backtrack from ${v} to ${u}: `;
        desc += `low[${v}]=${low[v]}, dfn[${u}]=${dfn[u]}. `;

        // Check bridge
        if (low[v] > dfn[u]) {
          bridges.push([u, v]);
          desc += `low[${v}] > dfn[${u}] (${low[v]} > ${dfn[u]}) → Bridge found: (${u},${v}). `;
        } else {
          desc += `low[${v}] > dfn[${u}]? ${low[v]} > ${dfn[u]}? No, not a bridge. `;
        }

        // Check articulation point
        if (low[v] >= dfn[u] && p !== null) {
          if (!articulations.includes(u)) {
            articulations.push(u);
            desc += `low[${v}] >= dfn[${u}] (${low[v]} >= ${dfn[u]}) → ${u} is an articulation point. `;
          }
        } else if (low[v] >= dfn[u] && p === null) {
          desc += `low[${v}] >= dfn[${u}] but ${u} is root. `;
        }

        if (lowChanged) {
          desc += `low[${u}] updated from ${oldLow} to ${low[u]}.`;
        } else {
          desc += `low[${u}] remains ${low[u]}.`;
        }

        addStep('backtrack', u, {
          neighbor: v,
          description: desc,
          highlightEdge: [v, u],
          highlightNode: u,
          lowUpdated: lowChanged ? { node: u, from: oldLow, to: low[u] } : null,
          newBridge: low[v] > dfn[u] ? [u, v] : null,
          newArticulation: low[v] >= dfn[u] && p !== null && !articulations.includes(u) ? u : null,
        });
      } else if (v !== p) {
        // Back edge
        const oldLow = low[u];
        low[u] = Math.min(low[u], dfn[v]);
        addStep('backedge', u, {
          neighbor: v,
          description: `Back edge ${u}→${v}: ${v} is already visited and not parent. low[${u}] = min(${oldLow}, dfn[${v}]=${dfn[v]}) = ${low[u]}.`,
          highlightEdge: [u, v],
          highlightNode: u,
          lowUpdated: oldLow !== low[u] ? { node: u, from: oldLow, to: low[u] } : null,
        });
      } else {
        addStep('skip_parent', u, {
          neighbor: v,
          description: `Explore edge ${u}→${v}: ${v} is the parent of ${u}, skip.`,
          highlightEdge: [u, v],
          highlightNode: u,
        });
      }
    }

    // After processing all children, check if root is articulation
    if (p === null && children > 1) {
      if (!articulations.includes(u)) {
        articulations.push(u);
        // Update the last step's description to include this
        const lastStep = steps[steps.length - 1];
        if (lastStep) {
          lastStep.description += ` Root ${u} has ${children} children → articulation point.`;
          lastStep.newArticulation = u;
        }
      }
    }
  }

  addStep('init', null, {
    description: 'Initialize: All nodes unvisited. dfn, low, and parent arrays are empty. Starting DFS from node A.',
    highlightNode: 'A',
  });

  dfs('A', null);

  addStep('complete', null, {
    description: `DFS complete! Articulation points: [${articulations.join(', ')}]. Bridges: [${bridges.map((b) => `(${b[0]},${b[1]})`).join(', ')}].`,
    highlightNode: null,
  });

  return steps;
}

// Build DFS steps for the modified graph (with edge C-E)
function buildModifiedSteps() {
  const steps = [];
  let time = 0;
  const dfn = {};
  const low = {};
  const parent = {};
  const articulations = [];
  const bridges = [];
  const visited = new Set();

  function addStep(type, node, extra = {}) {
    steps.push({
      type,
      node,
      dfn: { ...dfn },
      low: { ...low },
      parent: { ...parent },
      articulations: [...articulations],
      bridges: bridges.map((b) => [...b]),
      visited: new Set(visited),
      ...extra,
    });
  }

  function dfs(u, p) {
    visited.add(u);
    time++;
    dfn[u] = time;
    low[u] = time;
    parent[u] = p;
    let children = 0;

    addStep('visit', u, {
      description: `Visit node ${u}: dfn[${u}]=${dfn[u]}, low[${u}]=${low[u]}, parent[${u}]=${p || 'null'}`,
      highlightNode: u,
      newDfn: u,
    });

    const neighbors = graphDataModified.adjacency[u];
    for (const v of neighbors) {
      if (!visited.has(v)) {
        children++;
        addStep('explore', u, {
          neighbor: v,
          description: `Explore edge ${u}→${v}: ${v} is unvisited. Recursively call DFS(${v}).`,
          highlightEdge: [u, v],
          highlightNode: u,
        });

        dfs(v, u);

        const oldLow = low[u];
        low[u] = Math.min(low[u], low[v]);
        const lowChanged = oldLow !== low[u];

        let desc = `Backtrack from ${v} to ${u}: `;
        desc += `low[${v}]=${low[v]}, dfn[${u}]=${dfn[u]}. `;

        if (low[v] > dfn[u]) {
          bridges.push([u, v]);
          desc += `low[${v}] > dfn[${u}] (${low[v]} > ${dfn[u]}) → Bridge found: (${u},${v}). `;
        } else {
          desc += `low[${v}] > dfn[${u}]? ${low[v]} > ${dfn[u]}? No, not a bridge. `;
        }

        if (low[v] >= dfn[u] && p !== null) {
          if (!articulations.includes(u)) {
            articulations.push(u);
            desc += `low[${v}] >= dfn[${u}] (${low[v]} >= ${dfn[u]}) → ${u} is an articulation point. `;
          }
        }

        if (lowChanged) {
          desc += `low[${u}] updated from ${oldLow} to ${low[u]}.`;
        } else {
          desc += `low[${u}] remains ${low[u]}.`;
        }

        addStep('backtrack', u, {
          neighbor: v,
          description: desc,
          highlightEdge: [v, u],
          highlightNode: u,
          lowUpdated: lowChanged ? { node: u, from: oldLow, to: low[u] } : null,
          newBridge: low[v] > dfn[u] ? [u, v] : null,
          newArticulation: low[v] >= dfn[u] && p !== null && !articulations.includes(u) ? u : null,
        });
      } else if (v !== p) {
        const oldLow = low[u];
        low[u] = Math.min(low[u], dfn[v]);
        addStep('backedge', u, {
          neighbor: v,
          description: `Back edge ${u}→${v}: ${v} is already visited and not parent. low[${u}] = min(${oldLow}, dfn[${v}]=${dfn[v]}) = ${low[u]}.`,
          highlightEdge: [u, v],
          highlightNode: u,
          lowUpdated: oldLow !== low[u] ? { node: u, from: oldLow, to: low[u] } : null,
        });
      } else {
        addStep('skip_parent', u, {
          neighbor: v,
          description: `Explore edge ${u}→${v}: ${v} is the parent of ${u}, skip.`,
          highlightEdge: [u, v],
          highlightNode: u,
        });
      }
    }

    if (p === null && children > 1) {
      if (!articulations.includes(u)) {
        articulations.push(u);
        const lastStep = steps[steps.length - 1];
        if (lastStep) {
          lastStep.description += ` Root ${u} has ${children} children → articulation point.`;
          lastStep.newArticulation = u;
        }
      }
    }
  }

  addStep('init', null, {
    description: 'Initialize: All nodes unvisited. dfn, low, and parent arrays are empty. Starting DFS from node A. (Modified graph with edge C-E)',
    highlightNode: 'A',
  });

  dfs('A', null);

  addStep('complete', null, {
    description: `DFS complete! Articulation points: [${articulations.join(', ') || 'none'}]. Bridges: [${bridges.map((b) => `(${b[0]},${b[1]})`).join(', ') || 'none'}]. Note: With the added edge (C,E), (D,E) is no longer a bridge and D is no longer an articulation point!`,
    highlightNode: null,
  });

  return steps;
}

export const originalSteps = buildOriginalSteps();
export const modifiedSteps = buildModifiedSteps();

// Checkpoint questions mapped to step indices in the original steps
export const checkpointQuestions = [
  {
    id: 1,
    triggerStepIndex: 4, // After visiting B, before exploring its neighbors
    question: 'DFS has just visited node B (dfn[B]=2, low[B]=2). B has neighbors A, C, and D. Which node will be visited next and why?',
    options: [
      { id: 'a', text: 'A, because it is listed first in the adjacency list' },
      { id: 'b', text: 'C, because A is the parent of B and will be skipped' },
      { id: 'c', text: 'D, because it has the highest degree' },
      { id: 'd', text: 'A, because DFS always revisits the parent first' },
    ],
    correctAnswer: 'b',
    explanation: 'A is the parent of B (parent[B]=A), so the DFS skips it. Among the remaining unvisited neighbors C and D, DFS proceeds with C (the first unvisited neighbor in the adjacency list).',
  },
  {
    id: 2,
    triggerStepIndex: 15, // After backtracking from D to C
    question: 'After backtracking from D to C, low[C] was updated from 3 to 2. What caused this update?',
    options: [
      { id: 'a', text: 'A back edge from C to B was discovered' },
      { id: 'b', text: 'low[D] was 2, and low[C] = min(low[C], low[D]) = min(3, 2) = 2' },
      { id: 'c', text: 'dfn[C] was recalculated to be 2' },
      { id: 'd', text: 'The edge (C,D) was removed from the graph' },
    ],
    correctAnswer: 'b',
    explanation: 'During backtracking, a node updates its low value based on its children. Since low[D]=2 (D can reach B which has dfn=2), low[C] = min(3, 2) = 2. This means C can also reach an ancestor with dfn=2 through D.',
  },
  {
    id: 3,
    triggerStepIndex: 17, // After full backtracking, near completion
    question: 'What is the key difference between the bridge condition (low[child] > dfn[u]) and the articulation point condition (low[child] >= dfn[u])?',
    options: [
      { id: 'a', text: 'There is no difference; they are the same condition' },
      { id: 'b', text: 'The bridge condition requires strict inequality (>) because if low[child] == dfn[u], there is an alternative path to u, so the edge is not critical' },
      { id: 'c', text: 'The articulation point condition uses > while the bridge condition uses >=' },
      { id: 'd', text: 'Bridges are found with low[child] < dfn[u]' },
    ],
    correctAnswer: 'b',
    explanation: 'For a bridge, the edge (u, child) is the ONLY connection between the subtree and the rest of the graph, requiring low[child] > dfn[u] (the child cannot reach u or any ancestor of u). For an articulation point, if low[child] >= dfn[u], removing u disconnects that child\'s subtree, so u is critical even if low[child] == dfn[u].',
  },
  {
    id: 4,
    triggerStepIndex: 18, // At complete
    question: 'If you add an edge (C,E) to the original graph, what happens to the bridge (D,E)?',
    options: [
      { id: 'a', text: '(D,E) remains a bridge because D and E are still connected' },
      { id: 'b', text: '(D,E) is no longer a bridge because there is now an alternative path E-C-D' },
      { id: 'c', text: '(D,E) becomes a stronger bridge' },
      { id: 'd', text: 'The algorithm crashes because the graph now has a cycle' },
    ],
    correctAnswer: 'b',
    explanation: 'With the added edge (C,E), node E can now reach the rest of the graph through C even if (D,E) is removed. The alternative path E-C-D means low[E] would become 3 (dfn[C]) instead of 5, so low[E] > dfn[D] becomes 3 > 4 which is false. Thus (D,E) is no longer a bridge.',
  },
];
