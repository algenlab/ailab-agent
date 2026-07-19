import { ProblemInput, AlgorithmStep, RelaxedEdge } from './types';

export function runDijkstra(input: ProblemInput): {
  steps: AlgorithmStep[];
  finalAnswer: Record<string, number | string>;
} {
  const { start, weighted_graph } = input;
  const allNodes = Object.keys(weighted_graph);
  const distances: Record<string, number> = {};
  const visitedSet = new Set<string>();
  const heap: [number, string][] = [];

  for (const node of allNodes) {
    distances[node] = Infinity;
  }
  distances[start] = 0;
  heap.push([0, start]);

  const steps: AlgorithmStep[] = [];
  let stepNum = 0;

  steps.push({
    step: stepNum,
    poppedNode: null,
    poppedDistance: null,
    heapBefore: structuredClone(heap),
    heapAfter: structuredClone(heap),
    distances: { ...distances },
    visited: [],
    relaxedEdges: [],
    description: `初始化：设置起点 ${start} 距离为 0，其他节点距离为 ∞。将 (0, "${start}") 加入最小堆。`,
    isFinal: false,
  });

  while (heap.length > 0) {
    stepNum++;
    heap.sort((a, b) => a[0] - b[0]);
    const heapBefore: [number, string][] = structuredClone(heap);

    const [dist, node] = heap.shift()!;

    if (visitedSet.has(node)) {
      const heapAfter: [number, string][] = structuredClone(heap);
      steps.push({
        step: stepNum,
        poppedNode: node,
        poppedDistance: dist,
        heapBefore,
        heapAfter,
        distances: { ...distances },
        visited: Array.from(visitedSet),
        relaxedEdges: [],
        description: `弹出节点 "${node}" (距离 ${dist})，但该节点已访问过，跳过。`,
        isFinal: false,
      });
      continue;
    }

    visitedSet.add(node);
    const relaxedEdges: RelaxedEdge[] = [];

    for (const edge of weighted_graph[node] || []) {
      const candidate = dist + edge.weight;
      const oldDist = distances[edge.to];
      if (candidate < oldDist) {
        distances[edge.to] = candidate;
        heap.push([candidate, edge.to]);
        relaxedEdges.push({
          from: node,
          to: edge.to,
          weight: edge.weight,
          candidateDist: candidate,
          updated: true,
        });
      } else {
        relaxedEdges.push({
          from: node,
          to: edge.to,
          weight: edge.weight,
          candidateDist: candidate,
          updated: false,
        });
      }
    }

    const heapAfter: [number, string][] = structuredClone(heap);
    const descParts: string[] = [];
    descParts.push(`弹出节点 "${node}" (距离 ${dist})，标记为已访问。`);
    for (const re of relaxedEdges) {
      if (re.updated) {
        descParts.push(
          `松弛边 ${re.from}→${re.to} (权 ${re.weight})：候选距离 ${re.candidateDist} < 当前距离，更新 ${re.to} 距离为 ${re.candidateDist}。`
        );
      } else {
        descParts.push(
          `松弛边 ${re.from}→${re.to} (权 ${re.weight})：候选距离 ${re.candidateDist} ≥ 当前距离，不更新。`
        );
      }
    }
    if (relaxedEdges.length === 0) {
      descParts.push(`节点 "${node}" 没有出边。`);
    }

    steps.push({
      step: stepNum,
      poppedNode: node,
      poppedDistance: dist,
      heapBefore,
      heapAfter,
      distances: { ...distances },
      visited: Array.from(visitedSet),
      relaxedEdges,
      description: descParts.join(' '),
      isFinal: false,
    });
  }

  stepNum++;
  const formattedDistances: Record<string, number | string> = {};
  for (const node of allNodes) {
    formattedDistances[node] =
      distances[node] === Infinity ? '∞ (不可达)' : (distances[node] as number);
  }

  steps.push({
    step: stepNum,
    poppedNode: null,
    poppedDistance: null,
    heapBefore: [],
    heapAfter: [],
    distances: { ...formattedDistances },
    visited: Array.from(visitedSet),
    relaxedEdges: [],
    description: '算法结束。堆为空，所有可达节点的最短距离已确定。',
    isFinal: true,
  });

  return { steps, finalAnswer: formattedDistances };
}

export function formatDistance(d: number | string): string {
  if (typeof d === 'string') return d;
  if (d === Infinity) return '∞';
  return String(d);
}
