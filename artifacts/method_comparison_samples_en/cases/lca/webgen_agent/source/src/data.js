/* ================================================================
   Data Module: Tree structure, algorithm steps, and quiz questions
   ================================================================ */

/* ---------- Input Problem Data ---------- */
export const PROBLEM_INPUT = {
  p: "5",
  q: "1",
  tree: {
    edges: [
      ["3", "5"],
      ["3", "1"],
      ["5", "6"],
      ["5", "2"],
      ["1", "0"],
      ["1", "8"],
      ["2", "7"],
      ["2", "4"],
    ],
    nodes: [
      { id: "3" },
      { id: "5" },
      { id: "1" },
      { id: "6" },
      { id: "2" },
      { id: "0" },
      { id: "8" },
      { id: "7" },
      { id: "4" },
    ],
  },
};

export const FINAL_ANSWER = "3";

export const P_TARGET = "5";
export const Q_TARGET = "1";

/* ---------- Build Tree Structure ---------- */
// Node positions for SVG rendering (viewBox: 0 0 800 430)
export const NODE_POSITIONS = {
  "3": { x: 400, y: 60 },
  "5": { x: 220, y: 160 },
  "1": { x: 580, y: 160 },
  "6": { x: 140, y: 260 },
  "2": { x: 300, y: 260 },
  "0": { x: 500, y: 260 },
  "8": { x: 660, y: 260 },
  "7": { x: 250, y: 360 },
  "4": { x: 350, y: 360 },
};

// Build adjacency and child ordering from edges
function buildAdjacency(edges) {
  const children = {};
  const parentMap = {};
  for (const [parent, child] of edges) {
    if (!children[parent]) children[parent] = [];
    children[parent].push(child);
    parentMap[child] = parent;
  }
  return { children, parentMap };
}

const { children: TREE_CHILDREN, parentMap: TREE_PARENTS } = buildAdjacency(PROBLEM_INPUT.tree.edges);

// Identify root: node with no parent
const ROOT_ID = PROBLEM_INPUT.tree.nodes.find((n) => !TREE_PARENTS[n.id]).id;

// Build node objects with position, left, right children
export function buildTreeNodeMap() {
  const map = {};
  for (const node of PROBLEM_INPUT.tree.nodes) {
    const id = node.id;
    const kids = TREE_CHILDREN[id] || [];
    map[id] = {
      id,
      x: NODE_POSITIONS[id].x,
      y: NODE_POSITIONS[id].y,
      left: kids[0] || null,
      right: kids[1] || null,
      children: kids,
    };
  }
  return map;
}

export const TREE_NODE_MAP = buildTreeNodeMap();
export { ROOT_ID, TREE_CHILDREN, TREE_PARENTS };

/* ---------- Build Edge List for SVG ---------- */
export function buildEdgeList() {
  const edges = [];
  for (const id of Object.keys(TREE_NODE_MAP)) {
    const node = TREE_NODE_MAP[id];
    for (const childId of node.children) {
      const child = TREE_NODE_MAP[childId];
      edges.push({
        from: id,
        to: childId,
        x1: node.x,
        y1: node.y,
        x2: child.x,
        y2: child.y,
      });
    }
  }
  return edges;
}

export const EDGE_LIST = buildEdgeList();

/* ---------- Algorithm Steps ---------- */
// Each step represents a moment in the DFS-based LCA algorithm
export const ALGORITHM_STEPS = [
  {
    id: 0,
    phase: "start",
    currentNode: null,
    description:
      'Starting the LCA algorithm. We need to find the lowest common ancestor of p = "5" and q = "1" in the given binary tree. The algorithm uses recursive DFS: if the current node matches p or q, return it; otherwise recurse into left and right children. If both children return non-null, the current node is the LCA.',
    callStack: [],
    leftResult: null,
    rightResult: null,
    returnValue: null,
    highlightNodes: [],
    lcaFound: false,
  },
  {
    id: 1,
    phase: "enter",
    currentNode: "3",
    description:
      'Enter dfs(3). Node "3" is the root. It does not match p = "5" or q = "1", so we must recurse into the left child first. Calling dfs(5)...',
    callStack: ["dfs(3)"],
    leftResult: null,
    rightResult: null,
    returnValue: null,
    highlightNodes: ["3"],
    lcaFound: false,
  },
  {
    id: 2,
    phase: "enter",
    currentNode: "5",
    description:
      'Enter dfs(5). Node "5" matches p = "5"! According to the algorithm, when the current node equals p or q, we return it immediately without visiting its children (nodes 6 and 2). Return value: "5".',
    callStack: ["dfs(3)", "dfs(5)"],
    leftResult: null,
    rightResult: null,
    returnValue: "5",
    highlightNodes: ["5"],
    lcaFound: false,
  },
  {
    id: 3,
    phase: "backtrack",
    currentNode: "3",
    description:
      'Back at dfs(3). The left recursive call dfs(5) returned "5" (non-null). Now we must recurse into the right child. Calling dfs(1)...',
    callStack: ["dfs(3)"],
    leftResult: "5",
    rightResult: null,
    returnValue: null,
    highlightNodes: ["3", "5"],
    lcaFound: false,
  },
  {
    id: 4,
    phase: "enter",
    currentNode: "1",
    description:
      'Enter dfs(1). Node "1" matches q = "1"! Return it immediately without visiting its children (nodes 0 and 8). Return value: "1".',
    callStack: ["dfs(3)", "dfs(1)"],
    leftResult: null,
    rightResult: null,
    returnValue: "1",
    highlightNodes: ["1"],
    lcaFound: false,
  },
  {
    id: 5,
    phase: "lca_found",
    currentNode: "3",
    description:
      'Back at dfs(3). Left result = "5", Right result = "1". Both are non-null! This satisfies the LCA invariant: when both subtrees contain a target, the current node is the lowest common ancestor. Node "3" is the LCA. Final answer: "3".',
    callStack: [],
    leftResult: "5",
    rightResult: "1",
    returnValue: "3",
    highlightNodes: ["3", "5", "1"],
    lcaFound: true,
  },
];

/* ---------- Checkpoint Quiz Questions ---------- */
export const QUIZ_QUESTIONS = [
  {
    id: 0,
    scenario: "Alternate scenario: p = '7', q = '4'",
    question:
      "Suppose p = '7' and q = '4'. The current recursive node is 5, and the left child call dfs(6) returned null. Which node will be processed next?",
    options: ["6", "2", "1", "3"],
    correctIndex: 1,
    hint: "After the left child returns null, the algorithm proceeds to the right child of the current node.",
    explanation:
      "Since dfs(6) returned null (node 6 is neither p nor q and has no matching descendants), the algorithm moves to process the right child of node 5, which is node 2.",
  },
  {
    id: 1,
    scenario: "Alternate scenario: p = '7', q = '4'",
    question:
      "When processing node 2 recursively (p = '7', q = '4'), the left child dfs(7) returned '7' and the right child dfs(4) returned '4'. What should node 2 return?",
    options: ["'7'", "'4'", "'2'", "null"],
    correctIndex: 2,
    hint: "Recall the LCA invariant: when both left and right recursive calls return non-null values, what does the current node represent?",
    explanation:
      "When both left and right subtrees return a non-null result, it means each subtree contains one of the target nodes. Therefore, node 2 is the LCA for p = '7' and q = '4', and it should return itself: '2'.",
  },
  {
    id: 2,
    scenario: "Alternate scenario: p = '5', q = '6'",
    question:
      "In the same tree, if we keep p = '5' but change q to '6', what node becomes the LCA?",
    options: ["3", "5", "1", "6"],
    correctIndex: 1,
    hint: "Node 5 is an ancestor of node 6. When the algorithm reaches node 5, what happens?",
    explanation:
      "Node 5 matches p = '5' directly. Since the algorithm returns immediately upon finding a match, node 5 is returned before ever reaching node 6. Node 5 is the LCA because it is the deepest node that is an ancestor of both targets (itself and node 6).",
  },
  {
    id: 3,
    scenario: "Original scenario: p = '5', q = '1'",
    question:
      "In the recursion at node 3, the left child dfs(5) returned '5' and the right child dfs(1) returned '1'. Why does the final answer become '3'?",
    options: [
      "Because 3 is the root of the tree",
      "Because both subtrees contain a target, making 3 the deepest common ancestor",
      "Because 3 is the direct parent of both 5 and 1",
      "Because the algorithm always returns the root node",
    ],
    correctIndex: 1,
    hint: "Think about what it means when both the left and right recursive calls return non-null values.",
    explanation:
      "When both left and right recursive calls return non-null, it means one target was found in the left subtree and the other in the right subtree. The current node (3) is the deepest node that has both targets in its descendants, making it the lowest common ancestor.",
  },
];
