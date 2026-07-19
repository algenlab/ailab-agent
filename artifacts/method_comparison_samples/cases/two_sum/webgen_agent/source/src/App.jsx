import { useState, useCallback, useRef, useEffect } from 'react'
import ProblemDisplay from './components/ProblemDisplay'
import AlgorithmVisualizer from './components/AlgorithmVisualizer'
import CheckpointQuiz from './components/CheckpointQuiz'
import ActivityLog from './components/ActivityLog'

const PROBLEM_DATA = {
  nums: [2, 7, 11, 15],
  target: 9,
  answer: [0, 1]
}

const ALGORITHM_STATES = [
  {
    index: -1,
    phase: 'init',
    currentVal: null,
    need: null,
    seenBefore: {},
    seenAfter: {},
    found: false,
    result: null,
    description: '初始化：准备从 i=0 开始扫描数组，seen 哈希表为空。'
  },
  {
    index: 0,
    phase: 'processed',
    currentVal: 2,
    need: 7,
    seenBefore: {},
    seenAfter: { 2: 0 },
    found: false,
    result: null,
    description: 'i=0：nums[0]=2，计算 need = 9 - 2 = 7。在 seen {} 中未找到 7，将 {2: 0} 加入 seen，i 移至 1。'
  },
  {
    index: 1,
    phase: 'found',
    currentVal: 7,
    need: 2,
    seenBefore: { 2: 0 },
    seenAfter: { 2: 0 },
    found: true,
    result: [0, 1],
    description: 'i=1：nums[1]=7，计算 need = 9 - 7 = 2。在 seen {2: 0} 中找到了 2！返回 [seen[2], 1] = [0, 1]。'
  }
]

const PREDICTION_OPTIONS = [
  { id: 'A', text: '计算 need=2，在 seen 中找到 2，返回 [0, 1]' },
  { id: 'B', text: '计算 need=2，不在 seen 中，将 {7: 1} 加入 seen' },
  { id: 'C', text: '因为 target=9 已满足，停止扫描' },
  { id: 'D', text: '跳过 i=1，因为 7 大于 target' }
]
const PREDICTION_CORRECT = 'A'

const QUIZ_QUESTIONS = [
  {
    id: 'q1',
    question: '当前扫描到 nums[2]=11，seen 中已有 {2:0, 7:1}，target=9。下一步算法会执行什么操作？',
    options: [
      'A. 在 seen 中找到 11，返回 [2, 2]',
      'B. 计算 need = 9 - 11 = -2，不在 seen 中，将 {11: 2} 加入 seen，继续扫描',
      'C. 因为 need 为负数，直接返回空数组',
      'D. 重新从 i=0 开始扫描'
    ],
    correct: 1,
    explanation: 'need = target - nums[i] = 9 - 11 = -2。seen 中没有 -2，所以将 {11: 2} 加入 seen 并继续扫描。即使 need 为负，算法仍正常工作。',
    hint: 'need = target - current = 9 - 11 = -2。检查 seen 中是否有 -2 这个键。'
  },
  {
    id: 'q2',
    question: '在算法执行过程中，下面哪一项始终成立？',
    options: [
      'A. seen 的长度等于当前索引 i',
      'B. need 总是正数',
      'C. seen 中的键是已经访问过的元素值',
      'D. 算法总能找到解'
    ],
    correct: 2,
    explanation: 'seen 的定义是 seen[nums[i]] = i，记录每个已访问元素的值作为键。选项 A 不一定成立（可能存在重复值导致长度不增加）；B 不成立（need 可以为负）；D 不成立（可能无解）。',
    hint: '回顾 seen 的定义：每次迭代执行 seen[nums[i]] = i，键是元素的值。'
  },
  {
    id: 'q3',
    question: '将 nums[1] 从 7 改为 8，target 不变，算法是否还能找到解？请选择正确的输出。',
    options: [
      'A. 可以，返回 [0, 1]',
      'B. 可以，返回 [1, 2]',
      'C. 不能，返回 []',
      'D. 可以，返回 [0, 2]'
    ],
    correct: 2,
    explanation: '新数组为 [2, 8, 11, 15]，target=9。遍历：i=0 need=7 不在 {}；i=1 need=1 不在 {2:0}；i=2 need=-2 不在 {2:0,8:1}；i=3 need=-6 不在。最终返回空数组。',
    hint: '新数组 [2, 8, 11, 15]，target=9。尝试找哪两个数之和为 9？'
  },
  {
    id: 'q4',
    question: '当算法从 i=0 到 i=1 时，seen 经历了什么变化？为什么？',
    options: [
      'A. seen 不变，因为还没找到解',
      'B. seen 从 {} 变为 {2: 0}，因为 nums[0]=2 被记录',
      'C. seen 从 {} 变为 {7: 1}，因为 nums[1]=7 被记录',
      'D. seen 清空后重新记录'
    ],
    correct: 1,
    explanation: 'i=0 时 seen={}，检查 need=7 不在 seen 中，执行 seen[2]=0，哈希表变为 {2: 0}。这是 i=0 到 i=1 之间发生的唯一变化。',
    hint: 'i=0 时，算法检查后执行了什么操作？是添加当前值还是互补值？'
  }
]

export const ACTIVITY_ICONS = {
  nav: '📍',
  correct: '✅',
  incorrect: '❌',
  hint: '💡',
  answer: '👁️',
  info: '📋',
  checkpoint: '🔮'
}

export default function App() {
  const [currentState, setCurrentState] = useState(0)
  const [showProblemAnswer, setShowProblemAnswer] = useState(false)
  const [logEntries, setLogEntries] = useState([])
  const [checkpointActive, setCheckpointActive] = useState(false)
  const [checkpointAnswered, setCheckpointAnswered] = useState(false)
  const [checkpointFeedback, setCheckpointFeedback] = useState(null)
  const [quizAnswers, setQuizAnswers] = useState({})
  const [quizFeedback, setQuizFeedback] = useState({})
  const [activeQuizHints, setActiveQuizHints] = useState({})
  const [visualizerHint, setVisualizerHint] = useState(false)
  const logIdRef = useRef(0)

  const totalStates = ALGORITHM_STATES.length

  const addLog = useCallback((text, icon = 'info') => {
    const id = ++logIdRef.current
    setLogEntries(prev => [...prev, { id, text, icon, time: new Date().toLocaleTimeString('zh-CN', { hour12: false }) }])
  }, [])

  useEffect(() => {
    addLog('页面加载完成，准备开始学习两数之和算法。', 'info')
  }, [])

  const handleNext = useCallback(() => {
    if (currentState < totalStates - 1) {
      const nextState = currentState + 1
      if (currentState === 1 && nextState === 2 && !checkpointAnswered) {
        setCheckpointActive(true)
        addLog('到达预测关卡：需要预测 i=1 时算法的行为。', 'checkpoint')
        return
      }
      setCurrentState(nextState)
      const desc = ALGORITHM_STATES[nextState].description.substring(0, 40) + '...'
      addLog(`进入步骤 ${nextState}：${desc}`, 'nav')
    }
  }, [currentState, totalStates, checkpointAnswered, addLog])

  const handlePrev = useCallback(() => {
    if (currentState > 0) {
      if (checkpointActive) {
        setCheckpointActive(false)
        setCheckpointFeedback(null)
      }
      const prevState = currentState - 1
      setCurrentState(prevState)
      addLog(`返回步骤 ${prevState}`, 'nav')
    }
  }, [currentState, checkpointActive, addLog])

  const handleCheckpointAnswer = useCallback((optionId) => {
    const isCorrect = optionId === PREDICTION_CORRECT
    setCheckpointFeedback({ selected: optionId, correct: isCorrect })
    setCheckpointAnswered(true)
    setCheckpointActive(false)
    addLog(
      isCorrect
        ? `预测正确！选择了 "${optionId}"，算法确实会找到互补值并返回 [0, 1]。`
        : `预测不正确。选择了 "${optionId}"，正确答案是 A：在 seen 中找到 2，返回 [0, 1]。`,
      isCorrect ? 'correct' : 'incorrect'
    )
    setTimeout(() => {
      setCurrentState(2)
      addLog('进入步骤 2：算法成功找到解！', 'nav')
    }, 1200)
  }, [addLog])

  const handleSkipCheckpoint = useCallback(() => {
    setCheckpointActive(false)
    setCheckpointAnswered(true)
    setCheckpointFeedback(null)
    setCurrentState(2)
    addLog('跳过了预测关卡，直接查看结果。', 'nav')
  }, [addLog])

  const handleShowProblemAnswer = useCallback(() => {
    setShowProblemAnswer(true)
    addLog('查看了最终答案：[0, 1]', 'answer')
  }, [addLog])

  const handleQuizAnswer = useCallback((questionId, optionIndex) => {
    const question = QUIZ_QUESTIONS.find(q => q.id === questionId)
    const isCorrect = optionIndex === question.correct
    setQuizAnswers(prev => ({ ...prev, [questionId]: optionIndex }))
    setQuizFeedback(prev => ({ ...prev, [questionId]: { selected: optionIndex, correct: isCorrect } }))
    addLog(
      isCorrect
        ? `测验 ${questionId}：回答正确！`
        : `测验 ${questionId}：回答错误，选择了选项 ${String.fromCharCode(65 + optionIndex)}。`,
      isCorrect ? 'correct' : 'incorrect'
    )
  }, [addLog])

  const handleQuizHint = useCallback((questionId) => {
    setActiveQuizHints(prev => ({ ...prev, [questionId]: true }))
    addLog(`查看了测验 ${questionId} 的提示。`, 'hint')
  }, [addLog])

  const handleVisualizerHint = useCallback(() => {
    setVisualizerHint(true)
    addLog('查看了算法可视化提示。', 'hint')
  }, [addLog])

  const handleReset = useCallback(() => {
    setCurrentState(0)
    setShowProblemAnswer(false)
    setCheckpointActive(false)
    setCheckpointAnswered(false)
    setCheckpointFeedback(null)
    setQuizAnswers({})
    setQuizFeedback({})
    setActiveQuizHints({})
    setVisualizerHint(false)
    addLog('重置了所有学习进度。', 'info')
  }, [addLog])

  const isVisualizationComplete = currentState === totalStates - 1 && ALGORITHM_STATES[currentState].phase === 'found'

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">两数之和</h1>
        <span className="algorithm-badge">哈希表 / map</span>
        <button className="reset-btn" onClick={handleReset} title="重置学习进度">
          🔄 重置
        </button>
      </header>

      <main className="app-main">
        <ProblemDisplay
          nums={PROBLEM_DATA.nums}
          target={PROBLEM_DATA.target}
          answer={PROBLEM_DATA.answer}
          showAnswer={showProblemAnswer}
          onShowAnswer={handleShowProblemAnswer}
        />

        <AlgorithmVisualizer
          state={ALGORITHM_STATES[currentState]}
          stateIndex={currentState}
          totalStates={totalStates}
          nums={PROBLEM_DATA.nums}
          onNext={handleNext}
          onPrev={handlePrev}
          canGoNext={currentState < totalStates - 1}
          canGoPrev={currentState > 0}
          checkpointActive={checkpointActive}
          checkpointFeedback={checkpointFeedback}
          onCheckpointAnswer={handleCheckpointAnswer}
          onSkipCheckpoint={handleSkipCheckpoint}
          predictionOptions={PREDICTION_OPTIONS}
          predictionCorrect={PREDICTION_CORRECT}
          showHint={visualizerHint}
          onShowHint={handleVisualizerHint}
          isComplete={isVisualizationComplete}
        />

        <CheckpointQuiz
          questions={QUIZ_QUESTIONS}
          answers={quizAnswers}
          feedback={quizFeedback}
          activeHints={activeQuizHints}
          onAnswer={handleQuizAnswer}
          onHint={handleQuizHint}
          visible={isVisualizationComplete}
        />

        <ActivityLog entries={logEntries} />
      </main>
    </div>
  )
}