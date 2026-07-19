export interface SegmentTreeNode {
  id: number;
  l: number;
  r: number;
  sum: number;
  left: SegmentTreeNode | null;
  right: SegmentTreeNode | null;
}

export interface SegmentTree {
  root: SegmentTreeNode;
}

export interface AlgorithmState {
  step: 'initial' | 'built' | 'query' | 'update' | 'complete';
  tree: SegmentTree | null;
  before: number | null;
  after: number | null;
  highlightedPath: number[];
  visitedNodes: number[];
}

export interface Checkpoint {
  id: number;
  question: string;
  correctAnswer: string;
  context: string;
}

export interface ProblemInput {
  nums: number[];
  query: [number, number];
  update: [number, number];
}
