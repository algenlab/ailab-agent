import { useState, useMemo, useCallback } from 'react';
import { INPUT_GRAPH } from './data';

function buildAllSteps(graph) {
  const steps = [];
  const indegree = {};
  const nodes = Object.keys(graph);

  // Initialize indegree
  for (const node of nodes) {
    indegree[node] = 0;
  }
  for (const node of nodes) {
    for (const neighbor of graph[node]) {
      indegree[neighbor] = (indegree[neighbor] || 0) + 1;
    }
  }

  // Initial state
  const queue = nodes.filter(n => indegree[n] === 0).sort();
  const result = [];

  steps.push({
    indegree: { ...indegree },
    queue: [...queue],
    result: [...result],
    currentNode: null,
    changedNodes: [],
    description: '初始状态：计算 indegree，将 indegree=0 的节点加入队列'
  });

  // Simulate steps
  const workingIndegree = { ...indegree };
  const workingQueue = [...queue];
  const workingResult = [...result];

  while (workingQueue.length > 0) {
    const current = workingQueue.shift();
    workingResult.push(current);

    const changedNodes = [];
    for (const neighbor of (graph[current] || [])) {
      workingIndegree[neighbor] -= 1;
      changedNodes.push(neighbor);
      if (workingIndegree[neighbor] === 0) {
        workingQueue.push(neighbor);
      }
    }
    // Keep queue sorted for consistency
    workingQueue.sort();

    steps.push({
      indegree: { ...workingIndegree },
      queue: [...workingQueue],
      result: [...workingResult],
      currentNode: current,
      changedNodes: [...changedNodes],
      description: `弹出 ${current}，更新邻居 indegree，将新 indegree=0 的节点入队`
    });
  }

  // Final done step
  steps.push({
    indegree: { ...workingIndegree },
    queue: [],
    result: [...workingResult],
    currentNode: null,
    changedNodes: [],
    description: '算法结束：队列为空，已获得合法拓扑序列'
  });

  return steps;
}

export function useTopoSort() {
  const steps = useMemo(() => buildAllSteps(INPUT_GRAPH), []);
  const [stepIndex, setStepIndex] = useState(0);

  const goNext = useCallback(() => {
    setStepIndex(i => Math.min(i + 1, steps.length - 1));
  }, [steps.length]);

  const goPrev = useCallback(() => {
    setStepIndex(i => Math.max(i - 1, 0));
  }, []);

  const goReset = useCallback(() => {
    setStepIndex(0);
  }, []);

  const state = steps[stepIndex];
  const isDone = stepIndex === steps.length - 1;

  return { state, steps, stepIndex, goNext, goPrev, goReset, isDone };
}
