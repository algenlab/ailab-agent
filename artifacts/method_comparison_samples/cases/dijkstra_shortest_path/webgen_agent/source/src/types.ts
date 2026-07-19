export interface Edge {
  to: string;
  weight: number;
}

export interface Graph {
  [node: string]: Edge[];
}

export interface ProblemInput {
  start: string;
  weighted_graph: Graph;
}

export interface RelaxedEdge {
  from: string;
  to: string;
  weight: number;
  candidateDist: number;
  updated: boolean;
}

export interface AlgorithmStep {
  step: number;
  poppedNode: string | null;
  poppedDistance: number | null;
  heapBefore: [number, string][];
  heapAfter: [number, string][];
  distances: Record<string, number | string>;
  visited: string[];
  relaxedEdges: RelaxedEdge[];
  description: string;
  isFinal: boolean;
}

export interface QuizQuestion {
  id: number;
  type: 'multiple-choice' | 'numeric';
  question: string;
  options: string[];
  correctAnswer: string;
  explanation: string;
  hint: string;
}

export interface ActivityEntry {
  id: number;
  timestamp: string;
  action: string;
  detail: string;
  type: 'navigation' | 'answer' | 'hint' | 'reveal' | 'system';
}

export interface NodePosition {
  x: number;
  y: number;
}
