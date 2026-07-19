export const INPUT_GRAPH = {
  A: ['B', 'C'],
  B: ['D'],
  C: ['D'],
  D: []
};

export const EXPECTED_ANSWER = ['A', 'B', 'C', 'D'];

export const QUESTIONS = [
  {
    question: "当前 queue 头部是节点 'B'，请预测弹出 'B' 后，哪些邻居的 indegree 会变为 0 并将加入队列？",
    options: ['A', 'C', 'D', '无节点会变为 0'],
    answer: 'D',
    hint: "查看图：B 的邻居只有 D。弹出 B 后 D 的 indegree 从 1 减到 0，因此 D 会进入队列。"
  },
  {
    question: '在整个算法运行过程中，队列里始终满足什么不变性质？',
    options: [
      '队列中所有节点的 indegree 均为 0',
      '队列中所有节点的 indegree 均大于 0',
      '队列中节点按字母顺序排列',
      '队列长度始终等于 indegree 为 0 的节点数'
    ],
    answer: '队列中所有节点的 indegree 均为 0',
    hint: '只有 indegree 降为 0 的节点才会被加入队列，这是 Kahn 算法的核心不变量。'
  },
  {
    question: '在原图 graph 中添加一条边 D→A，使图产生环。描述这将如何影响算法行为？',
    options: [
      '算法会陷入无限循环',
      '算法会正常结束但结果不完整 — 部分节点永远无法进入队列',
      '算法会崩溃抛出异常',
      '算法会自动检测到环并跳过 D→A'
    ],
    answer: '算法会正常结束但结果不完整 — 部分节点永远无法进入队列',
    hint: '环中的节点 indegree 永远不会降为 0，队列提前变空，结果列表缺少环中的节点。'
  },
  {
    question: "当节点 'C' 从队列弹出后，indegree 和 queue 发生了哪些具体变化？为什么？",
    options: [
      "C 的邻居 D 的 indegree 从 1 减到 0，D 进入队列",
      "C 的邻居 D 的 indegree 从 2 减到 1，没有新节点入队",
      "C 的邻居 B 和 D 的 indegree 各减 1",
      "indegree 和 queue 都不变"
    ],
    answer: "C 的邻居 D 的 indegree 从 1 减到 0，D 进入队列",
    hint: "C 的邻居只有 D。弹出 C 前 D 的 indegree=1，减 1 后变为 0，D 入队。"
  }
];
