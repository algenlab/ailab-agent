import { ProblemInput, QuizQuestion } from './types';

export const problemInput: ProblemInput = {
  start: 'A',
  weighted_graph: {
    A: [
      { to: 'B', weight: 2 },
      { to: 'C', weight: 5 },
    ],
    B: [{ to: 'C', weight: 1 }],
    C: [],
  },
};

export const expectedAnswer: Record<string, number> = {
  A: 0,
  B: 2,
  C: 3,
};

export const nodePositions: Record<string, { x: number; y: number }> = {
  A: { x: 250, y: 90 },
  B: { x: 130, y: 290 },
  C: { x: 370, y: 290 },
};

export const quizQuestions: QuizQuestion[] = [
  {
    id: 1,
    type: 'multiple-choice',
    question:
      '当前堆为 [(1, "B"), (4, "C")]，距离记录：A:0, B:1, C:4。请问下一步将从堆中弹出哪个节点？',
    options: ['A', 'B', 'C', '无法确定'],
    correctAnswer: 'B',
    explanation:
      '最小堆总是弹出当前距离最小的节点。堆中 B 的距离为 1，C 的距离为 4，因此弹出距离最小的 B。',
    hint: '观察堆中每个节点对应的距离值，找出最小的那个。',
  },
  {
    id: 2,
    type: 'multiple-choice',
    question: '在执行 Dijkstra 算法的过程中，下列哪个陈述是始终成立的不变式？',
    options: [
      'A) 堆的大小等于未处理的节点数',
      'B) 已弹出（且首次访问）节点的最短距离不再更新',
      'C) 所有节点的当前距离都是最终最短路径',
    ],
    correctAnswer: 'B) 已弹出（且首次访问）节点的最短距离不再更新',
    explanation:
      'Dijkstra 算法的核心不变式：当节点首次从最小堆中弹出时，其当前记录的距离就是最终最短距离。此后不会再被更新。A 不正确，因为堆可能包含同一节点的多个副本。C 不正确，因为未处理节点的距离可能还会被更新。',
    hint: '思考节点从堆中首次弹出时的距离是否就是最终答案，以及堆中是否可能存在同一节点的多个条目。',
  },
  {
    id: 3,
    type: 'numeric',
    question:
      '如果将 start 改为 "B"，且边 (A, C) 的权值从 5 改为 2，请预测从 B 到 C 的最短时间。（输入数字）',
    options: [],
    correctAnswer: '1',
    explanation:
      '起点 B 距离为 0，B→C 权值为 1，因此 B 到 C 的最短时间为 1。边 (A, C) 权值改为 2 不影响结果，因为从 B 出发无法到达 A（没有指向 A 的边），A 不可达。',
    hint: '从 B 出发，检查 B 的出边权值。思考修改的边 (A, C) 是否在 B 的可达路径上。',
  },
  {
    id: 4,
    type: 'multiple-choice',
    question:
      '步骤中：弹出节点 B (距离 2)，发现 B→C 权 1，候选距离 3，而当前 C 距离为 5，因此更新 C 距离为 3。为什么会触发这次距离更新？',
    options: [
      'A) 因为算法规定必须按顺序处理每个节点',
      'B) 因为候选距离 3 小于当前记录距离 5，说明找到了一条更短的路径到达 C',
      'C) 因为 C 节点尚未被标记为已访问',
      'D) 因为堆中还有 C 节点的其他记录',
    ],
    correctAnswer: 'B) 因为候选距离 3 小于当前记录距离 5，说明找到了一条更短的路径到达 C',
    explanation:
      '松弛操作的核心思想：对于边 (u, v)，如果 dist[u] + weight(u,v) < dist[v]，说明通过 u 到达 v 比当前已知路径更短，因此更新 dist[v]。这里 2 + 1 = 3 < 5，触发更新。',
    hint: '比较"旧距离"和"新候选距离"的大小关系，这是松弛操作的核心判断条件。',
  },
];
