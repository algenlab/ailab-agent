import { useMemo } from 'react';

export function useAlgorithmSteps(nums) {
  const steps = useMemo(() => {
    if (!nums || nums.length === 0 || nums.some(isNaN)) {
      return [];
    }

    const n = nums.length;
    const dp = [];
    const stepList = [];

    for (let i = 0; i < n; i++) {
      let value, explanation;
      if (i === 0) {
        value = nums[0];
        explanation = `Base case: dp[0] = nums[0] = ${nums[0]}. Only the first house is available, so the thief robs it.`;
      } else if (i === 1) {
        value = Math.max(nums[0], nums[1]);
        explanation = `dp[1] = max(nums[0], nums[1]) = max(${nums[0]}, ${nums[1]}) = ${value}. The thief can rob either house 0 or house 1, whichever has more money.`;
      } else {
        const option1 = dp[i - 1];
        const option2 = dp[i - 2] + nums[i];
        value = Math.max(option1, option2);
        explanation = `dp[${i}] = max(dp[${i - 1}], dp[${i - 2}] + nums[${i}]) = max(${option1}, ${dp[i - 2]} + ${nums[i]} = ${option2}) = ${value}. The thief decides whether to skip house ${i} (keep dp[${i - 1}] = ${option1}) or rob house ${i} and add to dp[${i - 2}] (${dp[i - 2]} + ${nums[i]} = ${option2}).`;
      }
      dp.push(value);

      stepList.push({
        houseIndex: i,
        nums: [...nums],
        dp: [...dp],
        dpCurrentValue: value,
        explanation,
      });
    }

    return stepList;
  }, [nums]);

  const finalSteps = steps.length > 0 ? steps : [
    {
      houseIndex: 0,
      nums: [],
      dp: [],
      dpCurrentValue: 0,
      explanation: 'No valid input provided.',
    }
  ];

  const dpFinal = steps.length > 0 ? steps[steps.length - 1].dp : [];
  const finalAnswer = dpFinal.length > 0 ? dpFinal[dpFinal.length - 1] : 0;

  return { steps: finalSteps, dpFinal, finalAnswer };
}