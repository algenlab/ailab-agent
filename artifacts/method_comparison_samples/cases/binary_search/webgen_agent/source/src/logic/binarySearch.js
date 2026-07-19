export const initialState = {
  nums: [-1, 0, 3, 5, 9, 12],
  target: 9,
  answer: 4
};

export function generateSteps(nums, target) {
  const steps = [];
  let left = 0;
  let right = nums.length - 1;

  steps.push({
    phase: 'init',
    left,
    right,
    mid: null,
    nums,
    target,
    description: `初始化搜索区间: left = ${left}, right = ${right}，区间为 [${left}, ${right}]，包含所有 ${nums.length} 个元素。`,
    intervalElements: nums.slice(left, right + 1)
  });

  let iterCount = 0;
  while (left <= right) {
    iterCount++;
    const mid = Math.floor((left + right) / 2);
    const midVal = nums[mid];

    steps.push({
      phase: 'compute',
      left,
      right,
      mid,
      midVal,
      nums,
      target,
      description: `计算中点 mid = floor((${left} + ${right}) / 2) = ${mid}，nums[${mid}] = ${midVal}。`,
      intervalElements: nums.slice(left, right + 1)
    });

    if (midVal === target) {
      steps.push({
        phase: 'found',
        left,
        right,
        mid,
        midVal,
        nums,
        target,
        description: `🎯 nums[${mid}] = ${midVal} == target (${target})，找到目标值！返回索引 ${mid}。`,
        intervalElements: nums.slice(left, right + 1),
        found: true,
        answer: mid
      });
      return steps;
    } else if (midVal < target) {
      const oldLeft = left;
      left = mid + 1;
      steps.push({
        phase: 'discardLeft',
        left,
        right,
        mid,
        midVal,
        nums,
        target,
        oldLeft,
        description: `📘 nums[${mid}] = ${midVal} < target (${target})，目标在右半部分。丢弃左半 [${oldLeft}, ${mid}]，更新 left = mid + 1 = ${left}。新搜索区间: [${left}, ${right}]。`,
        intervalElements: nums.slice(left, right + 1)
      });
    } else {
      const oldRight = right;
      right = mid - 1;
      steps.push({
        phase: 'discardRight',
        left,
        right,
        mid,
        midVal,
        nums,
        target,
        oldRight,
        description: `📙 nums[${mid}] = ${midVal} > target (${target})，目标在左半部分。丢弃右半 [${mid}, ${oldRight}]，更新 right = mid - 1 = ${right}。新搜索区间: [${left}, ${right}]。`,
        intervalElements: nums.slice(left, right + 1)
      });
    }
  }

  steps.push({
    phase: 'notFound',
    left,
    right,
    mid: null,
    nums,
    target,
    description: `搜索区间为空 (left=${left} > right=${right})，target ${target} 不在数组中，返回 -1。`,
    intervalElements: [],
    found: false,
    answer: -1
  });

  return steps;
}
