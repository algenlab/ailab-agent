import React, { useState, useCallback, useRef, useEffect } from 'react'
import ProblemHeader from './components/ProblemHeader.jsx'
import InputOutputDisplay from './components/InputOutputDisplay.jsx'
import DpVisualization from './components/DpVisualization.jsx'
import LearnerQuiz from './components/LearnerQuiz.jsx'
import ActivityLog from './components/ActivityLog.jsx'
import { computeAllSteps, PROBLEM_INPUT } from './dpEngine.js'

const QUIZ_QUESTIONS = [
  {
    id: 1,
    question: '当前硬币面额 coin=2，容量 capacity=5，更新前 dp[5]=3，dp[3]=2。请预测更新后 dp[5] 的值。',
    answer: '2',
    explanation: 'dp[5] = min(dp[5], dp[5-2] + 1) = min(3, dp[3] + 1) = min(3, 2+1) = min(3, 3) = 3 → 等等，但这个例子中如果 dp[3]=2 且之前 dp[5]=3，min(3, 3)=3，结果仍是3。然而题目暗示硬币可重复使用，dp[5-2]=dp[3]=2，再加一枚硬币2即可凑5，所以 dp[5]=min(3, 3)=3（不变）。若 dp[3]=1，则更新为2。根据题目给出 dp[3]=2，所以 dp[5] 依然是 3。',
    fullExplanation: 'dp[5] = min(dp[5], dp[5-2] + 1) = min(3, dp[3] + 1) = min(3, 2 + 1) = min(3, 3) = 3。结果保持 3 不变，因为用一枚面额2的硬币加上凑3元的方案（2枚），总共需要3枚，与现有方案持平，不更新。'
  },
  {
    id: 2,
    question: '在完全背包零钱兑换中，无论 coins 和 amount 如何变化，哪个状态的数值始终保持不变？',
    answer: 'dp[0]',
    options: ['dp[0]', 'dp[1]', 'dp[amount]', 'dp[max(coins)]'],
    explanation: 'dp[0] 始终等于 0，因为凑出金额 0 不需要任何硬币。这是 DP 数组的基准状态。'
  },
  {
    id: 3,
    question: '原 coins=[1,2,5], amount=11，最少硬币数为 3。如果去掉面额 5，只留下 [1,2]，最少硬币数会变成多少？',
    answer: '6',
    explanation: '只用面额1和2凑11元：11 = 2×5 + 1×1，需要 5+1=6 枚硬币。验证：dp[11] = min(dp[10]+1, dp[9]+1)，递推得 6。'
  },
  {
    id: 4,
    question: '请解释当 coin=5, capacity=10 时，dp[10] 的更新为何要用 min(dp[10], dp[5]+1)。',
    answer: 'min',
    explanation: 'dp[10] 取"不使用当前硬币"（保持 dp[10] 原值）和"使用一枚面额5的硬币 + 凑剩余5元所需硬币数"（dp[5]+1）两者的最小值。正序更新使得 dp[5] 可能已经包含使用硬币5的情况，从而实现硬币的无限次重复使用。',
    isFreeResponse: true
  }
]

export default function App() {
  const [steps, setSteps] = useState(() => computeAllSteps(PROBLEM_INPUT))
  const [stepIndex, setStepIndex] = useState(0)
  const [quizState, setQuizState] = useState({})
  const [quizHistory, setQuizHistory] = useState({})
  const [activityLog, setActivityLog] = useState([
    { id: 0, type: 'system', message: '🎯 欢迎来到完全背包零钱兑换学习页面！请探索 DP 可视化并与测验互动。', time: new Date() }
  ])
  const logIdRef = useRef(1)

  const addLog = useCallback((type, message) => {
    const id = logIdRef.current++
    setActivityLog(prev => [...prev.slice(-49), { id, type, message, time: new Date() }])
  }, [])

  const handleStepChange = useCallback((dir) => {
    setStepIndex(prev => {
      const next = dir === 'next' ? Math.min(prev + 1, steps.length - 1) : Math.max(prev - 1, 0)
      if (next !== prev) {
        addLog('navigation', `导航至步骤 ${next + 1}/${steps.length}`)
      }
      return next
    })
  }, [steps.length, addLog])

  const handleJumpToStep = useCallback((idx) => {
    setStepIndex(idx)
    addLog('navigation', `跳转至步骤 ${idx + 1}/${steps.length}`)
  }, [steps.length, addLog])

  const handleQuizSubmit = useCallback((questionId, userAnswer) => {
    const q = QUIZ_QUESTIONS.find(x => x.id === questionId)
    const isCorrect = q.isFreeResponse
      ? userAnswer.toLowerCase().includes(q.answer.toLowerCase())
      : String(userAnswer).trim() === String(q.answer).trim()

    setQuizState(prev => ({ ...prev, [questionId]: { submitted: true, isCorrect, userAnswer } }))
    setQuizHistory(prev => ({ ...prev, [questionId]: isCorrect }))
    addLog(
      isCorrect ? 'correct' : 'incorrect',
      isCorrect
        ? `✅ 问题 #${questionId}：回答正确！`
        : `❌ 问题 #${questionId}：回答不正确。你的答案：${userAnswer}`
    )
  }, [addLog])

  const handleHint = useCallback((questionId) => {
    const q = QUIZ_QUESTIONS.find(x => x.id === questionId)
    addLog('hint', `💡 查看问题 #${questionId} 的提示：${q.explanation.slice(0, 60)}...`)
  }, [addLog])

  const handleShowAnswer = useCallback((questionId) => {
    const q = QUIZ_QUESTIONS.find(x => x.id === questionId)
    if (!quizState[questionId]?.submitted) {
      setQuizState(prev => ({ ...prev, [questionId]: { submitted: true, isCorrect: null, userAnswer: '[查看答案]', revealed: true } }))
      addLog('showAnswer', `👁️ 查看问题 #${questionId} 的答案：${q.answer}`)
    }
  }, [quizState, addLog])

  const allQuizDone = QUIZ_QUESTIONS.every(q => quizState[q.id]?.submitted)

  return (
    <div style={styles.wrapper}>
      <div style={styles.container}>
        <ProblemHeader />

        <InputOutputDisplay input={PROBLEM_INPUT} expectedAnswer={3} />

        <DpVisualization
          steps={steps}
          stepIndex={stepIndex}
          onStepChange={handleStepChange}
          onJumpToStep={handleJumpToStep}
          coins={PROBLEM_INPUT.coins}
          amount={PROBLEM_INPUT.amount}
        />

        <LearnerQuiz
          questions={QUIZ_QUESTIONS}
          quizState={quizState}
          quizHistory={quizHistory}
          onSubmit={handleQuizSubmit}
          onHint={handleHint}
          onShowAnswer={handleShowAnswer}
          allDone={allQuizDone}
        />

        <ActivityLog entries={activityLog} />
      </div>
    </div>
  )
}

const styles = {
  wrapper: {
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    padding: '24px 16px',
    background: 'linear-gradient(135deg, #e8edf5 0%, #f0f4f8 50%, #eef1f6 100%)',
  },
  container: {
    maxWidth: '960px',
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
}