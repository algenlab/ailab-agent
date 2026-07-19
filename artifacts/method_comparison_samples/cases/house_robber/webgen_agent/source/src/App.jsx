import React, { useState, useCallback, useMemo, useRef } from 'react';
import './App.css';

/* ---------- constants / pure helpers ---------- */
const PROBLEM_INPUT = [2, 7, 9, 3, 1];
const EXPECTED_ANSWER = 12;

function computeFullDp(nums) {
  const n = nums.length;
  if (n === 0) return [];
  const dp = [];
  const choice = []; // 'take' | 'skip' | null
  dp[0] = nums[0];
  choice[0] = 'take';
  if (n === 1) return { dp, choice };
  if (nums[1] >= nums[0]) {
    dp[1] = nums[1];
    choice[1] = 'take';
  } else {
    dp[1] = nums[0];
    choice[1] = 'skip';
  }
  for (let i = 2; i < n; i++) {
    const take = dp[i - 2] + nums[i];
    const skip = dp[i - 1];
    if (take >= skip) {
      dp[i] = take;
      choice[i] = 'take';
    } else {
      dp[i] = skip;
      choice[i] = 'skip';
    }
  }
  return { dp, choice };
}

const FULL_RESULT = computeFullDp(PROBLEM_INPUT);

/* ---------- checkpoint questions ---------- */
const CHECKPOINTS = [
  {
    id: 1,
    stepIndex: 2, // when dp[0], dp[1] are done and we are about to compute dp[2]
    question: '给定 nums = [2,7,9,3,1]，当前 dp[0]=2, dp[1]=7。当计算到 i=2 时，dp[2] 的值应为多少？',
    options: ['7', '9', '11', '16'],
    correct: 2,
    explanation: 'dp[2] = max(dp[1], dp[0] + nums[2]) = max(7, 2+9) = max(7,11) = 11。选择偷房屋2和房屋0。'
  },
  {
    id: 2,
    stepIndex: 4,
    question: '在 trace 中，当 i=3，nums=[2,7,9,3]，dp[2]=11 已算出，正要计算 dp[3]。请选择从状态 dp[2] 到 dp[3] 的正确决策过程：',
    options: [
      'dp[3] = dp[2] + nums[3] = 11 + 3 = 14',
      'dp[3] = max(dp[2], dp[1] + nums[3]) = max(11, 7+3) = max(11,10) = 11',
      'dp[3] = max(dp[1], dp[2]) = max(7, 11) = 11',
      'dp[3] = dp[1] + nums[3] = 7 + 3 = 10'
    ],
    correct: 1,
    explanation: 'dp[3] = max(dp[2], dp[1] + nums[3]) = max(11, 7+3) = max(11,10) = 11。不偷房屋3更优。'
  }
];

/* ---------- sub-components ---------- */

function LearningLog({ entries }) {
  return (
    <div className="log-panel">
      <h3>📝 学习日志</h3>
      <div className="log-entries">
        {entries.length === 0 && (
          <div className="log-empty">暂无记录。开始交互吧！</div>
        )}
        {entries.map((e, i) => (
          <div key={i} className={`log-entry log-${e.type}`}>
            <span className="log-time">{e.time}</span>
            <span className="log-msg">{e.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DpVisualizer({ nums, dp, choice, currentStep }) {
  return (
    <div className="dp-visualizer">
      <div className="dp-row dp-nums-row">
        <div className="dp-label">nums</div>
        {nums.map((val, i) => (
          <div
            key={i}
            className={`dp-cell nums-cell ${i === currentStep ? 'active' : ''} ${i < currentStep ? 'past' : ''}`}
          >
            <div className="cell-index">{i}</div>
            <div className="cell-value">{val}</div>
          </div>
        ))}
      </div>
      <div className="dp-row dp-dp-row">
        <div className="dp-label">dp</div>
        {nums.map((_, i) => {
          const computed = i <= currentStep;
          const value = computed ? dp[i] : '?';
          const decided = choice[i];
          return (
            <div
              key={i}
              className={`dp-cell dp-cell-dp ${computed ? 'filled' : 'pending'} ${i === currentStep ? 'active' : ''} ${decided === 'take' ? 'take' : decided === 'skip' ? 'skip' : ''}`}
            >
              <div className="cell-index">{i}</div>
              <div className="cell-value">{value}</div>
              {computed && decided && (
                <div className="cell-decision">{decided === 'take' ? '偷' : '不偷'}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StepDescription({ step, nums, dp, choice }) {
  const n = nums.length;
  if (step === -1) {
    return (
      <div className="step-desc">
        <p><strong>初始状态：</strong>准备开始计算。dp 数组尚未填充。</p>
        <p>递推公式：<code>dp[i] = max(dp[i-1], dp[i-2] + nums[i])</code></p>
      </div>
    );
  }
  if (step === 0) {
    return (
      <div className="step-desc">
        <p><strong>Step {step}：</strong>只有一间房屋，最优选择是偷它。</p>
        <p><code>dp[0] = nums[0] = {dp[0]}</code></p>
      </div>
    );
  }
  if (step === 1) {
    return (
      <div className="step-desc">
        <p><strong>Step {step}：</strong>前两间房屋，选择金额较大的那一间。</p>
        <p><code>dp[1] = max(nums[0], nums[1]) = max({nums[0]}, {nums[1]}) = {dp[1]}</code></p>
      </div>
    );
  }
  const take = dp[step - 2] + nums[step];
  const skip = dp[step - 1];
  return (
    <div className="step-desc">
      <p><strong>Step {step}：</strong>计算 <code>dp[{step}]</code></p>
      <ul>
        <li>偷当前房屋：<code>dp[{step - 2}] + nums[{step}] = {dp[step - 2]} + {nums[step]} = <strong>{take}</strong></code></li>
        <li>不偷当前房屋：<code>dp[{step - 1}] = <strong>{skip}</strong></code></li>
        <li>取最大值：<code>dp[{step}] = max({take}, {skip}) = <strong>{dp[step]}</strong></code> → <em>{choice[step] === 'take' ? '偷当前房屋' : '不偷当前房屋'}</em></li>
      </ul>
    </div>
  );
}

function CheckpointQuiz({ checkpoint, onAnswer, answered, result, onProceed }) {
  const [selected, setSelected] = useState(null);

  const handleSubmit = () => {
    if (selected === null) return;
    onAnswer(checkpoint.id, selected);
  };

  if (answered) {
    const isCorrect = result.correct;
    return (
      <div className={`checkpoint-quiz ${isCorrect ? 'correct' : 'incorrect'}`}>
        <div className="quiz-result-banner">
          {isCorrect ? '✅ 回答正确！' : '❌ 回答错误'}
        </div>
        <p className="quiz-explanation">{checkpoint.explanation}</p>
        <button className="btn btn-primary" onClick={onProceed}>继续</button>
      </div>
    );
  }

  return (
    <div className="checkpoint-quiz">
      <h4>💡 思考题</h4>
      <p>{checkpoint.question}</p>
      <div className="quiz-options">
        {checkpoint.options.map((opt, i) => (
          <label key={i} className={`quiz-option ${selected === i ? 'selected' : ''}`}>
            <input
              type="radio"
              name={`quiz-${checkpoint.id}`}
              checked={selected === i}
              onChange={() => setSelected(i)}
            />
            <span>{opt}</span>
          </label>
        ))}
      </div>
      <button
        className="btn btn-primary"
        disabled={selected === null}
        onClick={handleSubmit}
      >
        提交答案
      </button>
    </div>
  );
}

function InvariantQuestion({ onAnswer, answered, result }) {
  const [selected, setSelected] = useState(null);
  const options = [
    'dp[i] 总是严格递增的',
    'dp[i] >= dp[i-1]（单调不减）',
    'dp[i] = dp[i-1] + nums[i]',
    'dp[i] 总是偶数'
  ];
  const correctIdx = 1;
  const explanation = 'dp[i] 表示前 i 间房的最大收益，随着可选房屋增多，收益不会减少，因此 dp[i] >= dp[i-1] 始终成立（单调不减）。';

  if (answered) {
    return (
      <div className={`checkpoint-quiz ${result.correct ? 'correct' : 'incorrect'}`}>
        <div className="quiz-result-banner">
          {result.correct ? '✅ 回答正确！' : '❌ 回答错误'}
        </div>
        <p className="quiz-explanation">{explanation}</p>
      </div>
    );
  }

  return (
    <div className="checkpoint-quiz">
      <h4>🔍 不变式探究</h4>
      <p>观察整个算法执行过程中 dp 数组的变化，指出一个始终成立的不变式：</p>
      <div className="quiz-options">
        {options.map((opt, i) => (
          <label key={i} className={`quiz-option ${selected === i ? 'selected' : ''}`}>
            <input
              type="radio"
              name="invariant"
              checked={selected === i}
              onChange={() => setSelected(i)}
            />
            <span>{opt}</span>
          </label>
        ))}
      </div>
      <button
        className="btn btn-primary"
        disabled={selected === null}
        onClick={() => onAnswer('invariant', selected, correctIdx)}
      >
        提交答案
      </button>
    </div>
  );
}

function ManualCalcQuiz({ onAnswer, answered, result }) {
  const [input, setInput] = useState('');
  const correctAnswer = 4; // nums = [1,2,3,1] -> dp = [1,2,4,4] -> 4
  const explanation = 'nums = [1,2,3,1]\ndp[0] = 1\ndp[1] = max(1,2) = 2\ndp[2] = max(2, 1+3) = max(2,4) = 4\ndp[3] = max(4, 2+1) = max(4,3) = 4\n最高可偷金额 = 4';

  if (answered) {
    return (
      <div className={`checkpoint-quiz ${result.correct ? 'correct' : 'incorrect'}`}>
        <div className="quiz-result-banner">
          {result.correct ? '✅ 回答正确！' : '❌ 回答错误'}
        </div>
        <p className="quiz-explanation" style={{ whiteSpace: 'pre-line' }}>{explanation}</p>
      </div>
    );
  }

  return (
    <div className="checkpoint-quiz">
      <h4>🧮 手动计算</h4>
      <p>如果房屋金额改为 nums = [1, 2, 3, 1]，请手动计算最高可偷金额：</p>
      <div className="manual-input-row">
        <input
          type="number"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入答案"
          className="manual-input"
        />
        <button
          className="btn btn-primary"
          disabled={input === ''}
          onClick={() => onAnswer('manual', parseInt(input, 10), correctAnswer)}
        >
          提交
        </button>
      </div>
    </div>
  );
}

/* ---------- main app ---------- */
export default function App() {
  const [currentStep, setCurrentStep] = useState(-1); // -1 = before start
  const [logEntries, setLogEntries] = useState([]);
  const [quizResults, setQuizResults] = useState({});
  const [hintVisible, setHintVisible] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);
  const [invariantAnswered, setInvariantAnswered] = useState(false);
  const [manualAnswered, setManualAnswered] = useState(false);
  const logIdRef = useRef(0);

  const nums = PROBLEM_INPUT;
  const { dp, choice } = FULL_RESULT;
  const maxStep = nums.length - 1;

  const addLog = useCallback((type, message) => {
    const id = ++logIdRef.current;
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
    setLogEntries((prev) => [...prev, { id, type, time, message }]);
  }, []);

  const handleNext = useCallback(() => {
    if (currentStep < maxStep) {
      const next = currentStep + 1;
      setCurrentStep(next);
      addLog('action', `前进至 Step ${next}：计算 dp[${next}]`);
      setHintVisible(false);
    }
  }, [currentStep, maxStep, addLog]);

  const handlePrev = useCallback(() => {
    if (currentStep >= 0) {
      const prev = currentStep - 1;
      setCurrentStep(prev);
      addLog('action', prev >= 0 ? `回退至 Step ${prev}` : '回到初始状态');
      setHintVisible(false);
    }
  }, [currentStep, addLog]);

  const handleReset = useCallback(() => {
    setCurrentStep(-1);
    setQuizResults({});
    setHintVisible(false);
    setShowAnswer(false);
    setInvariantAnswered(false);
    setManualAnswered(false);
    addLog('action', '重置所有状态');
  }, [addLog]);

  const handleQuizAnswer = useCallback((quizId, selected) => {
    const cp = CHECKPOINTS.find((c) => c.id === quizId);
    const correct = selected === cp.correct;
    setQuizResults((prev) => ({ ...prev, [quizId]: { selected, correct } }));
    addLog(
      correct ? 'success' : 'error',
      `思考题 ${quizId}：${correct ? '回答正确 ✅' : '回答错误 ❌（选择了 ' + cp.options[selected] + '，正确答案是 ' + cp.options[cp.correct] + '）'}`
    );
  }, [addLog]);

  const handleInvariantAnswer = useCallback((key, selected, correctIdx) => {
    const correct = selected === correctIdx;
    setQuizResults((prev) => ({ ...prev, [key]: { selected, correct } }));
    setInvariantAnswered(true);
    addLog(
      correct ? 'success' : 'error',
      `不变式探究：${correct ? '回答正确 ✅' : '回答错误 ❌'}`
    );
  }, [addLog]);

  const handleManualAnswer = useCallback((key, value, correctAnswer) => {
    const correct = value === correctAnswer;
    setQuizResults((prev) => ({ ...prev, [key]: { selected: value, correct } }));
    setManualAnswered(true);
    addLog(
      correct ? 'success' : 'error',
      `手动计算：输入 ${value}，${correct ? '正确 ✅' : '错误 ❌（正确答案是 ' + correctAnswer + '）'}`
    );
  }, [addLog]);

  const handleHint = useCallback(() => {
    setHintVisible(true);
    addLog('hint', '查看了提示');
  }, [addLog]);

  const handleShowAnswer = useCallback(() => {
    setShowAnswer(true);
    setCurrentStep(maxStep);
    addLog('reveal', '查看了最终答案');
  }, [maxStep, addLog]);

  // Determine if a checkpoint should be shown at current step
  const activeCheckpoint = useMemo(() => {
    return CHECKPOINTS.find((cp) => cp.stepIndex === currentStep && !quizResults[cp.id]);
  }, [currentStep, quizResults]);

  const allDone = currentStep === maxStep;

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>🏠 打家劫舍</h1>
        <span className="algo-tag">一维 DP</span>
      </header>

      <div className="main-layout">
        {/* left column */}
        <div className="left-column">
          {/* problem card */}
          <section className="card problem-card">
            <h2>📋 问题描述</h2>
            <p>
              一位窃贼计划盗窃一条街上的若干房屋。房屋排列在一条直线上，每间房内藏有不同数额的现金。
              由于相邻房屋安装有联动警报，<strong>若连续盗窃相邻房屋，警报会被触发</strong>。
              请帮助窃贼计算在不触发警报的前提下，能够盗窃到的最高总金额。
            </p>
            <div className="io-block">
              <div className="io-item">
                <span className="io-label">输入 nums：</span>
                <code>[{nums.join(', ')}]</code>
              </div>
              <div className="io-item">
                <span className="io-label">期望答案：</span>
                <strong className="answer-value">{EXPECTED_ANSWER}</strong>
                {showAnswer && <span className="revealed-tag">（已展示）</span>}
              </div>
            </div>
          </section>

          {/* dp visualizer */}
          <section className="card viz-card">
            <div className="viz-header">
              <h2>📊 算法状态可视化</h2>
              <div className="step-indicator">
                {currentStep === -1 ? '初始状态' : `Step ${currentStep} / ${maxStep}`}
              </div>
            </div>
            <DpVisualizer
              nums={nums}
              dp={dp}
              choice={choice}
              currentStep={currentStep === -1 ? -1 : currentStep}
            />
            <StepDescription
              step={currentStep}
              nums={nums}
              dp={dp}
              choice={choice}
            />

            {/* nav controls */}
            <div className="nav-controls">
              <button className="btn btn-secondary" onClick={handlePrev} disabled={currentStep === -1}>
                ⬅ 上一步
              </button>
              <button className="btn btn-primary" onClick={handleNext} disabled={currentStep === maxStep}>
                下一步 ➡
              </button>
              <button className="btn btn-ghost" onClick={handleReset}>
                🔄 重置
              </button>
            </div>

            {/* hint */}
            <div className="hint-area">
              <button className="btn btn-outline" onClick={handleHint}>
                💡 提示
              </button>
              <button className="btn btn-outline" onClick={handleShowAnswer} disabled={showAnswer}>
                👁 显示答案
              </button>
              {hintVisible && (
                <div className="hint-box">
                  <p>
                    递推公式：<code>dp[i] = max(dp[i-1], dp[i-2] + nums[i])</code>
                  </p>
                  <p>
                    对于第 <strong>i</strong> 间房屋，你有两个选择：<br />
                    1. <strong>不偷</strong>：收益为 <code>dp[i-1]</code><br />
                    2. <strong>偷</strong>：收益为 <code>dp[i-2] + nums[i]</code>（跳过前一间）
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* checkpoints */}
          {activeCheckpoint && (
            <section className="card checkpoint-card">
              <CheckpointQuiz
                checkpoint={activeCheckpoint}
                onAnswer={handleQuizAnswer}
                answered={!!quizResults[activeCheckpoint.id]}
                result={quizResults[activeCheckpoint.id]}
                onProceed={() => {}}
              />
            </section>
          )}

          {allDone && !invariantAnswered && (
            <section className="card checkpoint-card">
              <InvariantQuestion
                onAnswer={handleInvariantAnswer}
                answered={invariantAnswered}
                result={quizResults['invariant']}
              />
            </section>
          )}

          {allDone && !manualAnswered && (
            <section className="card checkpoint-card">
              <ManualCalcQuiz
                onAnswer={handleManualAnswer}
                answered={manualAnswered}
                result={quizResults['manual']}
              />
            </section>
          )}
        </div>

        {/* right column */}
        <div className="right-column">
          <section className="card objectives-card">
            <h2>🎯 学习目标</h2>
            <ul>
              <li>理解状态 <code>dp[i]</code> 代表前 i 间房的最大收益及其递推关系</li>
              <li>从 trace 中的 dp 数组变化预测下一步计算</li>
              <li>识别并验证算法中的单调不变式（如 <code>dp[i] >= dp[i-1]</code>）</li>
            </ul>
          </section>

          <LearningLog entries={logEntries} />

          {/* answer reveal */}
          {showAnswer && (
            <section className="card answer-card">
              <h2>✅ 最终答案</h2>
              <div className="answer-display">
                <p>输入：<code>[{nums.join(', ')}]</code></p>
                <p>最高可偷金额：<strong className="answer-value">{EXPECTED_ANSWER}</strong></p>
                <p>DP 数组：<code>[{dp.join(', ')}]</code></p>
                <p>方案：偷索引 0 (<code>{nums[0]}</code>) 和索引 2 (<code>{nums[2]}</code>) 和索引 4 (<code>{nums[4]}</code>) = {nums[0]} + {nums[2]} + {nums[4]} = {nums[0] + nums[2] + nums[4]}</p>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}