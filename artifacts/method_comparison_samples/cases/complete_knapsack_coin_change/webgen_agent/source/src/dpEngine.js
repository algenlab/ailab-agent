export const PROBLEM_INPUT = {
  amount: 11,
  coins: [1, 2, 5]
}

export function computeAllSteps(input) {
  const { amount, coins } = input
  const INF = Infinity
  const dp = new Array(amount + 1).fill(INF)
  dp[0] = 0

  const steps = []

  // Initial state
  steps.push({
    type: 'initial',
    coin: null,
    capacity: null,
    dp: [...dp],
    description: `初始化：dp[0]=0，其余 dp[1..${amount}] 设为 ∞（不可达）`
  })

  for (const coin of coins) {
    steps.push({
      type: 'coin-start',
      coin,
      capacity: null,
      dp: [...dp],
      description: `开始处理硬币面额 coin=${coin}`
    })

    for (let c = coin; c <= amount; c++) {
      const oldVal = dp[c]
      const fromVal = dp[c - coin]
      const candidate = fromVal === INF ? INF : fromVal + 1
      const newVal = Math.min(oldVal, candidate)
      const updated = newVal !== oldVal

      steps.push({
        type: 'cell-update',
        coin,
        capacity: c,
        dp: [...dp],
        oldVal,
        candidate,
        newVal,
        updated,
        fromCapacity: c - coin,
        fromVal,
        description: updated
          ? `dp[${c}] = min(dp[${c}]=${oldVal === INF ? '∞' : oldVal}, dp[${c - coin}]+1 = ${fromVal === INF ? '∞' : fromVal}+1 = ${candidate === INF ? '∞' : candidate}) = ${newVal} ✅ 更新！`
          : `dp[${c}] = min(dp[${c}]=${oldVal === INF ? '∞' : oldVal}, dp[${c - coin}]+1 = ${fromVal === INF ? '∞' : fromVal}+1 = ${candidate === INF ? '∞' : candidate}) = ${newVal} → 不变`
      })

      dp[c] = newVal
    }

    steps.push({
      type: 'coin-end',
      coin,
      capacity: null,
      dp: [...dp],
      description: `硬币面额 coin=${coin} 处理完毕`
    })
  }

  // Final state
  const finalAnswer = dp[amount] === INF ? -1 : dp[amount]
  steps.push({
    type: 'final',
    coin: null,
    capacity: null,
    dp: [...dp],
    finalAnswer,
    description: finalAnswer === -1
      ? `无法凑出 amount=${amount} 元，返回 -1`
      : `最终答案：最少需要 ${finalAnswer} 枚硬币凑出 ${amount} 元`
  })

  return steps
}