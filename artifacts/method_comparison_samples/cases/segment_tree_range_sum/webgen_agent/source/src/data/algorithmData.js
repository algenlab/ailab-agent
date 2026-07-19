/**
 * 线段树节点定义
 * 每个节点: { id, l, r, sum, children }
 */
function buildSegmentTree(nums) {
  const nodes = [];
  const nodeMap = new Map();

  function build(l, r) {
    const id = `seg_${l}_${r}`;
    if (l === r) {
      const node = { id, l, r, sum: nums[l], children: [], isLeaf: true };
      nodes.push(node);
      nodeMap.set(id, node);
      return node;
    }
    const mid = Math.floor((l + r) / 2);
    const left = build(l, mid);
    const right = build(mid + 1, r);
    const node = { id, l, r, sum: left.sum + right.sum, children: [left, right], isLeaf: false };
    nodes.push(node);
    nodeMap.set(id, node);
    return node;
  }

  const root = build(0, nums.length - 1);
  return { root, nodes, nodeMap };
}

export const PROBLEM_DATA = {
  nums: [2, 1, 4, 5],
  query: [1, 3],
  update: [2, 6],
};

export const FINAL_ANSWER = { before: 10, after: 12 };

export const INITIAL_STATE = {
  nums: [2, 1, 4, 5],
  query: [1, 3],
  update: [2, 6],
};

// Build the tree for visualization
const originalTree = buildSegmentTree([2, 1, 4, 5]);
const updatedTree = buildSegmentTree([2, 1, 6, 5]);

// Pre-compute query paths
function queryPath(root, ql, qr) {
  const visited = [];
  const hits = [];
  function dfs(node) {
    visited.push(node.id);
    if (ql <= node.l && node.r <= qr) {
      hits.push(node.id);
      return;
    }
    if (node.isLeaf) return;
    const mid = Math.floor((node.l + node.r) / 2);
    if (ql <= mid) dfs(node.children[0]);
    if (qr > mid) dfs(node.children[1]);
  }
  dfs(root);
  return { visited, hits };
}

const originalQuery = queryPath(originalTree.root, 1, 3);
const updatedQuery = queryPath(updatedTree.root, 1, 3);

function buildAllTreeNodes(tree) {
  const order = [];
  function dfs(node) {
    if (node.children[0]) dfs(node.children[0]);
    order.push(node);
    if (node.children[1]) dfs(node.children[1]);
  }
  dfs(tree.root);
  const ids = ['seg_0_0', 'seg_0_1', 'seg_1_1', 'seg_0_3', 'seg_2_2', 'seg_2_3', 'seg_3_3'];
  return ids.map(id => tree.nodeMap.get(id)).filter(Boolean);
}

const allOriginalNodes = buildAllTreeNodes(originalTree);
const allUpdatedNodes = buildAllTreeNodes(updatedTree);

export const STEPS = [
  {
    id: 'step1',
    title: '问题理解',
    description: '我们有一个包裹重量数组 nums = [2, 1, 4, 5]（千克），需要查询区间 [1, 3] 的总重量，然后根据修正信息 update = [2, 6] 将第 2 小时的重量从 4 改为 6，再次查询同一区间。',
    highlightNodes: [],
    treeSnapshot: { nodes: allOriginalNodes, type: 'build' },
    subInfo: '目标：返回修正前总和 before 和修正后总和 after。',
  },
  {
    id: 'step2',
    title: '构建线段树 — 叶子节点',
    description: '线段树是一棵二叉树，每个叶子节点对应数组中的一个元素。叶子节点 seg_0_0 的 sum = nums[0] = 2，seg_1_1 sum = 1，seg_2_2 sum = 4，seg_3_3 sum = 5。',
    highlightNodes: ['seg_0_0', 'seg_1_1', 'seg_2_2', 'seg_3_3'],
    treeSnapshot: { nodes: allOriginalNodes, type: 'build-leaves' },
    subInfo: '叶子节点：左边界 l 等于右边界 r，直接存储数组元素值。',
  },
  {
    id: 'step3',
    title: '构建线段树 — 内部节点',
    description: '内部节点 seg_0_1 覆盖 [0, 1]，sum = seg_0_0.sum + seg_1_1.sum = 2 + 1 = 3。同理 seg_2_3 覆盖 [2, 3]，sum = 4 + 5 = 9。根节点 seg_0_3 覆盖 [0, 3]，sum = 3 + 9 = 12。',
    highlightNodes: ['seg_0_1', 'seg_2_3', 'seg_0_3'],
    treeSnapshot: { nodes: allOriginalNodes, type: 'build-inner' },
    subInfo: '父节点 sum = 左子 sum + 右子 sum。根节点 seg_0_3 代表整个数组的总和 12。',
  },
  {
    id: 'step4',
    title: '查询区间 [1, 3] — 修正前',
    description: '从根节点 seg_0_3 开始查询。seg_0_3 覆盖 [0, 3]，与查询区间 [1, 3] 部分重叠（不完全覆盖），进入子节点。seg_0_1 覆盖 [0, 1] 部分重叠，对其子节点查询：seg_0_0 覆盖 [0, 0] 不重叠，跳过；seg_1_1 覆盖 [1, 1] 完全在 [1, 3] 内，命中！sum += 1。seg_2_3 覆盖 [2, 3] 完全在 [1, 3] 内，命中！sum += 9。修正前 before = 1 + 9 = 10。',
    highlightNodes: ['seg_0_3', 'seg_0_1', 'seg_1_1', 'seg_2_3'],
    treeSnapshot: { nodes: allOriginalNodes, type: 'query-before', queryVisited: originalQuery.visited, queryHits: originalQuery.hits },
    subInfo: '查询结果：before = 10。只有 seg_1_1（sum=1）和 seg_2_3（sum=9）被完整命中。',
  },
  {
    id: 'step5',
    title: '执行单点更新 update=[2, 6]',
    description: '从根节点 seg_0_3 出发，沿路径找到叶子 seg_2_2（位置 2）。将 seg_2_2 的 sum 从 4 改为 6。然后回溯更新父节点：seg_2_3.sum = seg_2_2.sum + seg_3_3.sum = 6 + 5 = 11，seg_0_3.sum = seg_0_1.sum + seg_2_3.sum = 3 + 11 = 14。',
    highlightNodes: ['seg_0_3', 'seg_2_3', 'seg_2_2'],
    treeSnapshot: { nodes: allUpdatedNodes, type: 'update', updatePath: ['seg_0_3', 'seg_2_3', 'seg_2_2'] },
    subInfo: '更新路径：seg_0_3 → seg_2_3 → seg_2_2，逐层向上回溯维护父节点 sum。',
  },
  {
    id: 'step6',
    title: '重新查询区间 [1, 3] — 修正后',
    description: '更新后数组变为 [2, 1, 6, 5]。再次查询 [1, 3]：seg_1_1 命中（sum=1），seg_2_3 命中（新 sum=11）。修正后 after = 1 + 11 = 12。',
    highlightNodes: ['seg_1_1', 'seg_2_3', 'seg_0_3'],
    treeSnapshot: { nodes: allUpdatedNodes, type: 'query-after', queryVisited: updatedQuery.visited, queryHits: updatedQuery.hits },
    subInfo: '最终结果：{"before": 10, "after": 12}。单点更新的时间复杂度为 O(log n)。',
  },
];
