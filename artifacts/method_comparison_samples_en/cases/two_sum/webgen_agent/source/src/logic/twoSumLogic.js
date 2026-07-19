/**
 * Two Sum algorithm logic — one-pass hash table scan.
 *
 * Each step object describes the state after processing index i:
 *   - i: current scan position
 *   - seen: hash table mapping value -> index
 *   - need: target - nums[i] for the current step
 *   - found: boolean indicating if complement was found at this step
 *   - result: the pair of indices if found, otherwise null
 *   - completed: boolean indicating algorithm is done
 */

export function createInitialState(input) {
  return {
    i: -1,
    seen: {},
    need: null,
    found: false,
    result: null,
    completed: false,
    nums: [...input.nums],
    target: input.target
  };
}

export function computeAllSteps(input) {
  const { nums, target } = input;
  const steps = [];
  const seen = {};

  for (let i = 0; i < nums.length; i++) {
    const need = target - nums[i];
    if (need in seen) {
      steps.push({
        i,
        seen: { ...seen },
        need,
        found: true,
        result: [seen[need], i],
        completed: true,
        nums: [...nums],
        target
      });
      return steps;
    }
    const step = {
      i,
      seen: { ...seen },
      need,
      found: false,
      result: null,
      completed: false,
      nums: [...nums],
      target
    };
    steps.push(step);
    seen[nums[i]] = i;
  }

  // If we finish loop without finding, add a final "not found" step
  if (nums.length > 0 && steps.length === nums.length) {
    steps.push({
      i: nums.length,
      seen: { ...seen },
      need: null,
      found: false,
      result: null,
      completed: true,
      nums: [...nums],
      target
    });
  }

  return steps;
}

export function computeNextStep(prevState) {
  const { nums, target, seen, i: prevI } = prevState;
  const i = prevI + 1;
  if (i >= nums.length) {
    return {
      ...prevState,
      i: nums.length,
      need: null,
      found: false,
      result: null,
      completed: true
    };
  }
  const need = target - nums[i];
  const newSeen = { ...seen };
  if (need in seen) {
    return {
      i,
      seen: newSeen,
      need,
      found: true,
      result: [seen[need], i],
      completed: true,
      nums: [...nums],
      target
    };
  }
  newSeen[nums[i]] = i;
  return {
    i,
    seen: newSeen,
    need,
    found: false,
    result: null,
    completed: false,
    nums: [...nums],
    target
  };
}