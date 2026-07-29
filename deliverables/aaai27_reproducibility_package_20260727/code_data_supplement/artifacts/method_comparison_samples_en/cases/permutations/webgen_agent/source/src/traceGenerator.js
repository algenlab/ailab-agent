/**
 * Generates a step-by-step trace of the backtracking permutation algorithm.
 * Each step records the state of path, used array, depth, and accumulated results.
 */

export function generateTrace(nums) {
  const steps = [];
  const results = [];

  function backtrack(path, used) {
    if (path.length === nums.length) {
      results.push([...path]);
      steps.push({
        type: 'complete',
        path: [...path],
        used: [...used],
        depth: path.length,
        index: -1,
        value: null,
        results: results.map((r) => [...r]),
        description: `Complete permutation found: [${path.join(', ')}]. Added to results. (Total results so far: ${results.length})`
      });
      return;
    }

    for (let i = 0; i < nums.length; i++) {
      if (!used[i]) {
        // Select
        used[i] = true;
        path.push(nums[i]);
        steps.push({
          type: 'select',
          path: [...path],
          used: [...used],
          depth: path.length,
          index: i,
          value: nums[i],
          results: results.map((r) => [...r]),
          description: `Select nums[${i}] = ${nums[i]}. Now path = [${path.join(', ')}], used = [${used.map((b) => (b ? 'T' : 'F')).join(', ')}], depth = ${path.length}`
        });

        backtrack(path, used);

        // Backtrack
        const popped = path.pop();
        used[i] = false;
        steps.push({
          type: 'backtrack',
          path: [...path],
          used: [...used],
          depth: path.length,
          index: i,
          value: popped,
          results: results.map((r) => [...r]),
          description: `Backtrack: pop ${popped} from path, unmark used[${i}]. Now path = [${path.join(', ')}], used = [${used.map((b) => (b ? 'T' : 'F')).join(', ')}], depth = ${path.length}`
        });
      }
    }
  }

  // Initial state
  const initialUsed = nums.map(() => false);
  steps.push({
    type: 'start',
    path: [],
    used: [...initialUsed],
    depth: 0,
    index: -1,
    value: null,
    results: [],
    description: `Start: path = [], used = [${initialUsed.map((b) => (b ? 'T' : 'F')).join(', ')}], depth = 0. Ready to explore all permutations of [${nums.join(', ')}].`
  });

  backtrack([], [...initialUsed]);

  // Final summary step
  steps.push({
    type: 'finish',
    path: [],
    used: initialUsed.map(() => false),
    depth: 0,
    index: -1,
    value: null,
    results: results.map((r) => [...r]),
    description: `Finished! All ${results.length} permutations of [${nums.join(', ')}] have been generated. The algorithm explored every possible ordering systematically.`
  });

  return steps;
}

export const PROBLEM_INPUT = [1, 2, 3];
export const EXPECTED_OUTPUT = [
  [1, 2, 3],
  [1, 3, 2],
  [2, 1, 3],
  [2, 3, 1],
  [3, 1, 2],
  [3, 2, 1]
];