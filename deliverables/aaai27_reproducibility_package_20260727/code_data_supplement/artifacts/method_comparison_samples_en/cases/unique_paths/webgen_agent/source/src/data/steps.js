const M = 3;
const N = 7;

/**
 * Precompute every step of the DP table fill.
 * Each step records which cell is filled, its dependency values,
 * and a snapshot of the entire dp table up to that point.
 */
export function generateSteps() {
  const dp = Array.from({ length: M }, () => Array(N).fill(null));
  const steps = [];

  for (let i = 0; i < M; i++) {
    for (let j = 0; j < N; j++) {
      const above = i > 0 ? dp[i - 1][j] : null;
      const left = j > 0 ? dp[i][j - 1] : null;

      let value;
      if (i === 0 && j === 0) {
        value = 1;
      } else if (i === 0) {
        value = left;
      } else if (j === 0) {
        value = above;
      } else {
        value = above + left;
      }

      dp[i][j] = value;

      steps.push({
        cell: [i, j],
        above,
        left,
        value,
        dpSnapshot: dp.map((row) => [...row]),
      });
    }
  }

  return { steps, m: M, n: N };
}

export const PROBLEM_INPUT = { m: 3, n: 7 };
export const EXPECTED_ANSWER = 28;
