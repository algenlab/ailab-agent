import { SegmentTreeNode, SegmentTree } from './types';

let nodeIdCounter = 0;

function resetIdCounter(): void {
  nodeIdCounter = 0;
}

function getNextId(): number {
  return nodeIdCounter++;
}

export function buildSegmentTree(
  nums: number[],
  l: number,
  r: number
): SegmentTree {
  resetIdCounter();
  const root = buildNode(nums, l, r);
  return { root };
}

function buildNode(nums: number[], l: number, r: number): SegmentTreeNode {
  const id = getNextId();
  if (l === r) {
    return {
      id,
      l,
      r,
      sum: nums[l],
      left: null,
      right: null,
    };
  }
  const mid = Math.floor((l + r) / 2);
  const left = buildNode(nums, l, mid);
  const right = buildNode(nums, mid + 1, r);
  return {
    id,
    l,
    r,
    sum: left.sum + right.sum,
    left,
    right,
  };
}

export function queryRange(
  tree: SegmentTree,
  ql: number,
  qr: number,
  visited: number[]
): number {
  return queryNode(tree.root, ql, qr, visited);
}

function queryNode(
  node: SegmentTreeNode,
  ql: number,
  qr: number,
  visited: number[]
): number {
  visited.push(node.id);
  // Complete overlap
  if (ql <= node.l && node.r <= qr) {
    return node.sum;
  }
  // No overlap
  if (node.r < ql || node.l > qr) {
    return 0;
  }
  // Partial overlap
  let total = 0;
  if (node.left) {
    total += queryNode(node.left, ql, qr, visited);
  }
  if (node.right) {
    total += queryNode(node.right, ql, qr, visited);
  }
  return total;
}

export function updatePoint(
  tree: SegmentTree,
  pos: number,
  value: number,
  updatePath: number[]
): SegmentTree {
  const newRoot = updateNode(tree.root, pos, value, updatePath);
  return { root: newRoot };
}

function updateNode(
  node: SegmentTreeNode,
  pos: number,
  value: number,
  updatePath: number[]
): SegmentTreeNode {
  const updated: SegmentTreeNode = {
    ...node,
    left: node.left ? { ...node.left } : null,
    right: node.right ? { ...node.right } : null,
  };

  if (node.l === node.r) {
    // Leaf node
    updated.sum = value;
    updatePath.push(node.id);
    return updated;
  }

  const mid = Math.floor((node.l + node.r) / 2);
  if (pos <= mid && updated.left) {
    updated.left = updateNode(updated.left, pos, value, updatePath);
  } else if (updated.right) {
    updated.right = updateNode(updated.right, pos, value, updatePath);
  }

  updated.sum = (updated.left?.sum ?? 0) + (updated.right?.sum ?? 0);
  updatePath.push(node.id);
  return updated;
}

export function cloneTree(tree: SegmentTree): SegmentTree {
  return {
    root: cloneNode(tree.root),
  };
}

function cloneNode(node: SegmentTreeNode): SegmentTreeNode {
  return {
    ...node,
    left: node.left ? cloneNode(node.left) : null,
    right: node.right ? cloneNode(node.right) : null,
  };
}

export function getNodesAtLevel(tree: SegmentTree): SegmentTreeNode[][] {
  const levels: SegmentTreeNode[][] = [];
  if (!tree.root) return levels;
  let currentLevel: SegmentTreeNode[] = [tree.root];
  while (currentLevel.length > 0) {
    levels.push([...currentLevel]);
    const nextLevel: SegmentTreeNode[] = [];
    for (const node of currentLevel) {
      if (node.left) nextLevel.push(node.left);
      if (node.right) nextLevel.push(node.right);
    }
    currentLevel = nextLevel;
  }
  return levels;
}

export function getAllNodes(tree: SegmentTree): SegmentTreeNode[] {
  const nodes: SegmentTreeNode[] = [];
  collectNodes(tree.root, nodes);
  return nodes;
}

function collectNodes(node: SegmentTreeNode, out: SegmentTreeNode[]): void {
  out.push(node);
  if (node.left) collectNodes(node.left, out);
  if (node.right) collectNodes(node.right, out);
}
