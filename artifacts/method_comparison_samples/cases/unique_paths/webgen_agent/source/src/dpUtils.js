/**
 * Compute the full DP table for unique paths problem.
 * dp[i][j] = number of unique paths from (0,0) to (i,j)
 *   moving only right or down.
 * Base: dp[i][0] = 1, dp[0][j] = 1
 * Recurrence: dp[i][j] = dp[i-1][j] + dp[i][j-1]
 */
export function computeDPTable(m, n) {
  const dp = Array.from({ length: m }, () => Array(n).fill(0));
  for (let i = 0; i < m; i++) {
    for (let j = 0; j < n; j++) {
      if (i === 0 || j === 0) {
        dp[i][j] = 1;
      } else {
        dp[i][j] = dp[i - 1][j] + dp[i][j - 1];
      }
    }
  }
  return dp;
}

/**
 * Generate the ordered list of cells in DP computation order (row-major).
 * Each step: { i, j, value, dependencies: [{i, j, value}], isEdge }
 */
export function generateSteps(m, n) {
  const dp = computeDPTable(m, n);
  const steps = [];
  for (let i = 0; i < m; i++) {
    for (let j = 0; j < n; j++) {
      const deps = [];
      if (i > 0) deps.push({ i: i - 1, j, value: dp[i - 1][j] });
      if (j > 0) deps.push({ i, j: j - 1, value: dp[i][j - 1] });
      steps.push({
        i,
        j,
        value: dp[i][j],
        dependencies: deps,
        isEdge: i === 0 || j === 0
      });
    }
  }
  return { steps, dp };
}

/**
 * Compute binomial coefficient C(k, r) = k!/(r!*(k-r)!)
 * Total paths = C(m+n-2, m-1) = C(m+n-2, n-1)
 */
export function combinationPaths(m, n) {
  const N = m + n - 2;
  const R = Math.min(m - 1, n - 1);
  let result = 1;
  for (let i = 1; i <= R; i++) {
    result = result * (N - R + i) / i;
  }
  return Math.round(result);
}

/**
 * Generate learning questions based on current state.
 */
export function generateQuestions(m, n, stepIndex, steps) {
  if (!steps || steps.length === 0) return [];

  const questions = [];
  const current = steps[Math.min(stepIndex, steps.length - 1)];

  // Question about predicting next value (when we're partway through)
  if (stepIndex > 0 && stepIndex < steps.length - 1) {
    const next = steps[stepIndex + 1];
    if (!next.isEdge) {
      const upVal = next.dependencies.find(d => d.i === next.i - 1)?.value;
      const leftVal = next.dependencies.find(d => d.j === next.j - 1)?.value;
      if (upVal !== undefined && leftVal !== undefined) {
        questions.push({
          id: 'predict',
          question: `当前正在计算 dp[${next.i}][${next.j}]，它的上方 dp[${next.i - 1}][${next.j}] = ${upVal}，左侧 dp[${next.i}][${next.j - 1}] = ${leftVal}。请预测 dp[${next.i}][${next.j}] 的值应为多少？`,
          answer: next.value,
          hint: `根据状态转移方程 dp[i][j] = dp[i−1][j] + dp[i][j−1]，将上方值 ${upVal} 和左侧值 ${leftVal} 相加即可得到 ${upVal} + ${leftVal} = ${next.value}。`,
          isTextual: false
        });
      }
    }
  }

  // Question about first row/column (early in the process)
  if (stepIndex >= 0 && stepIndex < steps.length * 0.5) {
    questions.push({
      id: 'edge',
      question: '观察 DP 表格，第一行 dp[0][j] 和第一列 dp[i][0] 的值始终为 1，请解释为什么它们不会改变。',
      answer: '因为从起点到第一行的任何格子只有一条路径（一直向右），到第一列也只有一条路径（一直向下），没有其他选择。',
      hint: '想一想机器人只能向右或向下移动。从起点到第一行的某个格子，只能一直向右走；到第一列只能一直向下走。没有其他路径可选，所以始终为 1。',
      isTextual: true
    });
  }

  // Question about why dp[i][j] = dp[i-1][j] + dp[i][j-1] (mid-process)
  if (stepIndex >= Math.floor(steps.length * 0.3) && stepIndex < steps.length - 1) {
    const mid = steps[stepIndex];
    if (!mid.isEdge) {
      const upVal = mid.dependencies.find(d => d.i === mid.i - 1)?.value;
      const leftVal = mid.dependencies.find(d => d.j === mid.j - 1)?.value;
      questions.push({
        id: 'why-sum',
        question: `解释为什么 dp[${mid.i}][${mid.j}] 等于 dp[${mid.i - 1}][${mid.j}]（=${upVal}）和 dp[${mid.i}][${mid.j - 1}]（=${leftVal}）的和。请用机器人的移动规则说明。`,
        answer: `到达 (${mid.i}, ${mid.j}) 的最后一步只能从上方 (${mid.i - 1}, ${mid.j}) 向下，或从左侧 (${mid.i}, ${mid.j - 1}) 向右。所以路径总数是两者之和。`,
        hint: `机器人只能向右或向下移动。要到达格子 (${mid.i}, ${mid.j})，最后一步要么从上方下来，要么从左侧过来。因此总路径数 = 到达上方格子的路径数 + 到达左侧格子的路径数。`,
        isTextual: true
      });
    }
  }

  // Question about combination formula (toward the end)
  if (stepIndex >= Math.floor(steps.length * 0.6)) {
    const total = combinationPaths(m, n);
    const newM = m + 1;
    const newAnswer = combinationPaths(newM, n);
    questions.push({
      id: 'combo',
      question: `如果将网格从当前 m = ${m}, n = ${n} 改为 m = ${newM}, n = ${n}（行数加一），新的路径总数会是多少？请基于组合数公式 C(m + n − 2, m − 1) 推理。`,
      answer: newAnswer,
      hint: `原组合数：C(${m + n - 2}, ${m - 1}) = ${total}。新参数 m′ = ${newM}, n′ = ${n}，公式为 C(${newM + n - 2}, ${newM - 1}) = C(${newM + n - 2}, ${m}) = ${newAnswer}。`,
      isTextual: false
    });
  }

  return questions;
}
