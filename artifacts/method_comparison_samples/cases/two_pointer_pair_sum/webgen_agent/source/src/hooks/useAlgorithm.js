import { useReducer, useCallback, useMemo } from 'react';

function buildSteps(nums, target) {
  const steps = [];
  let left = 0;
  let right = nums.length - 1;
  
  // Initial state
  steps.push({
    left,
    right,
    sum: nums[left] + nums[right],
    found: false,
    description: `初始化：左指针指向开头 (index 0, 值=${nums[0]})，右指针指向末尾 (index ${right}, 值=${nums[right]})`,
  });

  while (left < right) {
    const sum = nums[left] + nums[right];
    if (sum === target) {
      steps.push({
        left,
        right,
        sum,
        found: true,
        description: `找到匹配！nums[${left}]=${nums[left]} + nums[${right}]=${nums[right]} = ${sum} = target=${target}`,
      });
      break;
    } else if (sum < target) {
      left++;
      const newSum = nums[left] + nums[right];
      steps.push({
        left,
        right,
        sum: newSum,
        found: false,
        description: `sum=${sum} < target=${target}，左指针右移 → left=${left}，新 sum=${newSum}`,
      });
    } else {
      right--;
      const newSum = nums[left] + nums[right];
      steps.push({
        left,
        right,
        sum: newSum,
        found: false,
        description: `sum=${sum} > target=${target}，右指针左移 → right=${right}，新 sum=${newSum}`,
      });
    }
  }

  // If no match found and left >= right
  if (steps.length > 0 && !steps[steps.length - 1].found && left >= right) {
    // Already captured the last comparison; add terminal state
    steps[steps.length - 1] = {
      ...steps[steps.length - 1],
      found: false,
      description: steps[steps.length - 1].description + ' — 指针相遇，未找到匹配组合',
    };
  }

  return steps;
}

const initialState = {
  currentStep: 0,
  steps: [],
};

function reducer(state, action) {
  switch (action.type) {
    case 'INIT':
      return {
        currentStep: 0,
        steps: action.steps,
      };
    case 'STEP_FORWARD':
      if (state.currentStep >= state.steps.length - 1) return state;
      return { ...state, currentStep: state.currentStep + 1 };
    case 'STEP_BACKWARD':
      if (state.currentStep <= 0) return state;
      return { ...state, currentStep: state.currentStep - 1 };
    case 'GO_TO_STEP':
      if (action.step < 0 || action.step >= state.steps.length) return state;
      return { ...state, currentStep: action.step };
    case 'RESET':
      return { ...state, currentStep: 0 };
    default:
      return state;
  }
}

export function useAlgorithm(nums, target) {
  const [state, dispatch] = useReducer(reducer, initialState, () => {
    const steps = buildSteps(nums, target);
    return { currentStep: 0, steps };
  });

  const steps = useMemo(() => buildSteps(nums, target), [nums, target]);

  // Re-initialize if inputs change
  const init = useCallback(() => {
    dispatch({ type: 'INIT', steps: buildSteps(nums, target) });
  }, [nums, target]);

  // Ensure steps are built (for initial render)
  if (state.steps.length === 0) {
    // This happens before useEffect; use useMemo'd steps
    dispatch({ type: 'INIT', steps });
  }

  const stepForward = useCallback(() => dispatch({ type: 'STEP_FORWARD' }), []);
  const stepBackward = useCallback(() => dispatch({ type: 'STEP_BACKWARD' }), []);
  const reset = useCallback(() => dispatch({ type: 'RESET' }), []);
  const goToStep = useCallback((step) => dispatch({ type: 'GO_TO_STEP', step }), []);

  const currentStepData = state.steps[state.currentStep] || { left: 0, right: nums.length - 1, sum: nums[0] + nums[nums.length - 1], found: false };
  const isComplete = currentStepData.found || (currentStepData.left >= currentStepData.right && state.currentStep === state.steps.length - 1);

  const getCurrentState = useCallback(() => currentStepData, [currentStepData]);

  return {
    state: currentStepData,
    steps: state.steps,
    currentStep: state.currentStep,
    isComplete,
    found: currentStepData.found ? [currentStepData.left, currentStepData.right] : null,
    stepForward,
    stepBackward,
    reset,
    goToStep,
    getCurrentState,
  };
}