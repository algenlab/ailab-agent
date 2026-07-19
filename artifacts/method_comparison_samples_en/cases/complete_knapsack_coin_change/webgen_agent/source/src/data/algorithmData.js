/**
 * Generates all DP steps for the unbounded coin change problem.
 * Each step captures the full dp array state plus metadata for visualization.
 */

const INF = Infinity;

export function generateSteps(amount, coins) {
  const dp = new Array(amount + 1).fill(INF);
  dp[0] = 0;
  const steps = [];

  // Step 0: initial state
  steps.push({
    id: 0,
    type: 'init',
    coin: null,
    capacity: null,
    dp: [...dp],
    highlightIndex: 0,
    referenceIndex: null,
    oldValue: null,
    newValue: 0,
    changed: false,
    description: 'Initialize dp array. dp[0] = 0 (zero coins needed to make amount 0). All other entries set to ∞ (unreachable).'
  });

  let stepId = 1;

  for (const coin of coins) {
    // Coin-start step
    steps.push({
      id: stepId++,
      type: 'coin-start',
      coin,
      capacity: null,
      dp: [...dp],
      highlightIndex: null,
      referenceIndex: null,
      oldValue: null,
      newValue: null,
      changed: false,
      description: `Start processing coin denomination ${coin}. We will attempt to improve dp[c] for all capacities c from ${coin} to ${amount} using this coin.`
    });

    for (let c = coin; c <= amount; c++) {
      const oldVal = dp[c];
      const refVal = dp[c - coin];
      const candidate = refVal === INF ? INF : refVal + 1;
      const newVal = Math.min(oldVal, candidate);
      const changed = oldVal !== newVal;

      if (changed) {
        dp[c] = newVal;
      }

      const fmtOld = oldVal === INF ? '∞' : oldVal;
      const fmtRef = refVal === INF ? '∞' : refVal;
      const fmtCand = candidate === INF ? '∞' : candidate;
      const fmtNew = newVal === INF ? '∞' : newVal;

      steps.push({
        id: stepId++,
        type: 'update',
        coin,
        capacity: c,
        dp: [...dp],
        highlightIndex: c,
        referenceIndex: c - coin,
        oldValue: oldVal,
        newValue: newVal,
        changed,
        description: `coin=${coin}, capacity=${c}: dp[${c}] = min(${fmtOld}, dp[${c - coin}]+1) = min(${fmtOld}, ${fmtRef}+1) = min(${fmtOld}, ${fmtCand}) = ${fmtNew}${changed ? ' ✓ updated' : ' (no change)'}`
      });
    }
  }

  return { steps, finalDp: dp, finalAnswer: dp[amount] === INF ? -1 : dp[amount] };
}

/**
 * Build checkpoint definitions keyed by step index.
 * We scan the generated steps to find the right positions.
 */
export function buildCheckpoints(steps) {
  const checkpoints = [];

  // Q2 (early): Which state remains constant? — place after init
  checkpoints.push({
    id: 'q2',
    triggerStepId: steps[0].id,
    title: 'Checkpoint: Invariant State',
    question: 'In the complete knapsack coin change problem, regardless of how coins and amount change, which state\'s value remains constant?',
    type: 'multiple-choice',
    options: ['dp[0]', 'dp[amount]', 'dp[1]', 'None — all values can change'],
    correctIndex: 0,
    explanation: 'dp[0] always equals 0 because zero coins are needed to make amount 0. This is the base case and never changes during the algorithm.',
    hint: 'Think about the base case. What amount requires zero coins?'
  });

  // Q1: Find the step where coin=2, capacity=5
  const q1Step = steps.find(s => s.type === 'update' && s.coin === 2 && s.capacity === 5);
  if (q1Step) {
    checkpoints.push({
      id: 'q1',
      triggerStepId: q1Step.id,
      title: 'Checkpoint: Predict the Update',
      question: 'Current coin denomination coin=2, capacity=5. Before the update, dp[5]=3, dp[3]=2. Predict the value of dp[5] after the update.',
      type: 'multiple-choice',
      options: ['2', '3', '4', '5'],
      correctIndex: 1,
      explanation: 'dp[5] = min(dp[5], dp[5-2]+1) = min(3, dp[3]+1) = min(3, 2+1) = min(3, 3) = 3. The value remains 3 because using two 2-coins is not better than the existing solution.',
      hint: 'Compute dp[5-2]+1 and compare it with the current dp[5].'
    });
  }

  // Q4: Find the step where coin=5, capacity=10
  const q4Step = steps.find(s => s.type === 'update' && s.coin === 5 && s.capacity === 10);
  if (q4Step) {
    checkpoints.push({
      id: 'q4',
      triggerStepId: q4Step.id,
      title: 'Checkpoint: Explain the Transition',
      question: 'Explain why when coin=5, capacity=10, the update of dp[10] uses min(dp[10], dp[5]+1).',
      type: 'multiple-choice',
      options: [
        'Because dp[5] stores the minimum coins for amount 5, and adding one 5-coin gives a candidate solution for amount 10.',
        'Because dp[10] and dp[5] are always equal.',
        'Because the algorithm randomly picks dp[5] as a reference.',
        'Because 10 divided by 5 equals 2, which is dp[5].'
      ],
      correctIndex: 0,
      explanation: 'Using one coin of denomination 5 reduces the remaining amount to 5 (since 10-5=5). dp[5] already stores the optimal (minimum) number of coins to make amount 5. So dp[5]+1 is a valid candidate for dp[10].',
      hint: 'Think about what happens after you use one 5-coin. How much amount is left, and what does dp[that amount] tell you?'
    });
  }

  // Q3: After all steps — what if we remove coin 5?
  checkpoints.push({
    id: 'q3',
    triggerStepId: steps[steps.length - 1].id,
    title: 'Checkpoint: What-If Analysis',
    question: 'Original coins=[1,2,5], amount=11, minimum coins=3. If we remove denomination 5, leaving only [1,2], what will be the minimum number of coins for amount=11?',
    type: 'multiple-choice',
    options: ['3', '5', '6', '11'],
    correctIndex: 2,
    explanation: 'With only coins [1,2], the optimal solution for amount 11 is five 2-coins (10) plus one 1-coin (1) = 6 coins total. Removing the 5-coin forces a less efficient solution.',
    hint: 'Try to make 11 using only 1s and 2s. Use as many 2s as possible, then fill the remainder with 1s.'
  });

  // Map step ID -> checkpoint
  const checkpointMap = {};
  for (const cp of checkpoints) {
    checkpointMap[cp.triggerStepId] = cp;
  }

  return { checkpoints, checkpointMap };
}
