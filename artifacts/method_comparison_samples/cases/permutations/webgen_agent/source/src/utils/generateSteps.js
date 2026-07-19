/**
 * Generate all algorithm steps for the backtracking permutation algorithm.
 * Each step captures the complete state at a meaningful point in the algorithm.
 */
export function generateSteps(nums) {
  const steps = [];
  const n = nums.length;
  const result = [];

  function backtrack(path, used, depth) {
    if (path.length === n) {
      result.push([...path]);
      steps.push({
        id: steps.length,
        action: 'complete',
        path: [...path],
        used: [...used],
        result: result.map(r => [...r]),
        depth,
        candidateIndex: null,
        description: `✅ 找到完整排列: [${path.join(', ')}]`,
        highlightPath: true,
      });
      return;
    }

    for (let i = 0; i < n; i++) {
      const skipped = used[i];

      steps.push({
        id: steps.length,
        action: 'try',
        path: [...path],
        used: [...used],
        result: result.map(r => [...r]),
        depth,
        candidateIndex: i,
        description: skipped
          ? `⏭ 跳过 nums[${i}]=${nums[i]}（已使用）`
          : `🔍 检查 nums[${i}]=${nums[i]}（未使用，可选）`,
        highlightPath: false,
      });

      if (!used[i]) {
        used[i] = true;
        path.push(nums[i]);

        steps.push({
          id: steps.length,
          action: 'select',
          path: [...path],
          used: [...used],
          result: result.map(r => [...r]),
          depth: depth + 1,
          candidateIndex: i,
          description: `➕ 选择 nums[${i}]=${nums[i]}，加入 path → [${path.join(', ')}]`,
          highlightPath: true,
        });

        backtrack(path, used, depth + 1);

        path.pop();
        used[i] = false;

        steps.push({
          id: steps.length,
          action: 'backtrack',
          path: [...path],
          used: [...used],
          result: result.map(r => [...r]),
          depth,
          candidateIndex: i,
          description: `↩ 回溯：撤销 nums[${i}]=${nums[i]}，path 恢复为 [${path.join(', ') || '空'}]`,
          highlightPath: false,
        });
      }
    }
  }

  const path = [];
  const used = new Array(n).fill(false);

  steps.push({
    id: 0,
    action: 'init',
    path: [],
    used: [...used],
    result: [],
    depth: 0,
    candidateIndex: null,
    description: `🚀 开始回溯搜索，nums = [${nums.join(', ')}]，初始 path=[]，used 全为 false`,
    highlightPath: false,
  });

  backtrack(path, used, 0);

  steps.push({
    id: steps.length,
    action: 'done',
    path: [],
    used: new Array(n).fill(false),
    result: result.map(r => [...r]),
    depth: 0,
    candidateIndex: null,
    description: `🎉 搜索完成！共找到 ${result.length} 个全排列`,
    highlightPath: false,
  });

  return steps;
}
