import React, { useState, useCallback, useRef, useEffect } from 'react';
import AlgorithmVisualizer from './components/AlgorithmVisualizer';
import QuizPanel from './components/QuizPanel';
import ActivityLog from './components/ActivityLog';
import { useAlgorithm } from './hooks/useAlgorithm';
import { PROBLEM_DATA } from './data/problemData';

export default function App() {
  const {
    state,
    steps,
    currentStep,
    isComplete,
    found,
    stepForward,
    stepBackward,
    reset,
    goToStep,
    getCurrentState,
  } = useAlgorithm(PROBLEM_DATA.nums, PROBLEM_DATA.target);

  const [quizState, setQuizState] = useState('idle');
  const [quizResult, setQuizResult] = useState(null);
  const [showHint, setShowHint] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);
  const [logEntries, setLogEntries] = useState([]);
  const [autoPlaying, setAutoPlaying] = useState(false);
  const autoPlayRef = useRef(null);

  const addLog = useCallback((icon, message) => {
    const now = new Date();
    const time = now.toLocaleTimeString('zh-CN', { hour12: false });
    setLogEntries(prev => [...prev, { id: Date.now() + Math.random(), time, icon, message }]);
  }, []);

  useEffect(() => {
    return () => {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    };
  }, []);

  const handleStepForward = useCallback(() => {
    if (isComplete) return;
    stepForward();
    addLog('▶️', '执行了一步：向前移动指针');
  }, [isComplete, stepForward, addLog]);

  const handleStepBackward = useCallback(() => {
    if (currentStep <= 0) return;
    stepBackward();
    addLog('◀️', '回退了一步');
  }, [currentStep, stepBackward, addLog]);

  const handleReset = useCallback(() => {
    reset();
    setQuizState('idle');
    setQuizResult(null);
    setShowHint(false);
    setShowAnswer(false);
    if (autoPlayRef.current) {
      clearInterval(autoPlayRef.current);
      setAutoPlaying(false);
    }
    addLog('🔄', '重置算法，回到初始状态');
  }, [reset, addLog]);

  const handleAutoPlay = useCallback(() => {
    if (autoPlaying) {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
      setAutoPlaying(false);
      addLog('⏸️', '停止自动播放');
      return;
    }
    if (isComplete) return;
    setAutoPlaying(true);
    addLog('▶️', '开始自动播放');
    autoPlayRef.current = setInterval(() => {
      stepForward();
    }, 1200);
  }, [autoPlaying, isComplete, stepForward, addLog]);

  useEffect(() => {
    if (isComplete && autoPlaying) {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
      setAutoPlaying(false);
      if (found) {
        addLog('✅', '自动播放完成：找到匹配组合！');
      } else {
        addLog('⏹️', '自动播放完成：未找到匹配组合');
      }
    }
  }, [isComplete, autoPlaying, found, addLog]);

  const handleHint = useCallback(() => {
    setShowHint(true);
    addLog('💡', '查看了提示');
  }, [addLog]);

  const handleShowAnswer = useCallback(() => {
    setShowAnswer(true);
    addLog('👁️', '查看了最终答案');
  }, [addLog]);

  const handleQuizAnswer = useCallback((selectedAnswer, isCorrect, correctAnswer) => {
    setQuizState('answered');
    setQuizResult({ selected: selectedAnswer, correct: isCorrect, correctAnswer });
    if (isCorrect) {
      addLog('🎉', `测验回答正确！选择了"${selectedAnswer}"`);
    } else {
      addLog('❌', `测验回答错误。选择了"${selectedAnswer}"，正确答案是"${correctAnswer}"`);
    }
  }, [addLog]);

  const handleStartQuiz = useCallback(() => {
    setQuizState('active');
    setQuizResult(null);
    addLog('📝', '开始测验：预测下一步指针移动');
  }, [addLog]);

  const currState = getCurrentState();

  const sumCompareResult = currState.sum === PROBLEM_DATA.target
    ? 'sum = target ✓'
    : currState.sum < PROBLEM_DATA.target
      ? 'sum < target → 移动左指针'
      : 'sum > target → 移动右指针';

  const sumCompareColor = currState.sum === PROBLEM_DATA.target
    ? 'var(--success)'
    : currState.sum < PROBLEM_DATA.target
      ? 'var(--warning)'
      : 'var(--error)';

  return (
    <div className="container">
      {/* Header */}
      <header className="header">
        <h1>有序数组两数之和</h1>
        <div className="subtitle">
          <span className="badge">数组指针</span>
          <span className="badge">窗口</span>
          <span className="badge">前缀</span>
          <span>双指针算法 · 交互式学习</span>
        </div>
      </header>

      {/* Problem Description */}
      <div className="card">
        <div className="card-title"><span className="icon">📋</span> 问题描述</div>
        <p style={{ marginBottom: 14, fontSize: '0.92rem', lineHeight: 1.85 }}>
          在电商促销活动中，你作为选品助手，要从按价格升序排列的商品清单 <code>nums</code> 中，
          找出两件商品，让它们的总价恰好等于用户持有的 <code>target</code> 元优惠券面额。
          你需要返回这两个商品在列表中的下标（从0开始）；如果没有这种组合，就返回一个空列表。
        </p>

        <div className="row">
          <div className="col">
            <div style={{ fontWeight: 600, marginBottom: 6, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              📥 输入 (Input)
            </div>
            <div className="io-block">
              <span className="bracket">{'{'}</span>
              {'\n  '}<span className="key">"nums"</span>: <span className="bracket">[</span>
              {PROBLEM_DATA.nums.map((n, i) => (
                <span key={i}><span className="value">{n}</span>{i < PROBLEM_DATA.nums.length - 1 ? ', ' : ''}</span>
              ))}
              <span className="bracket">]</span>,
              {'\n  '}<span className="key">"target"</span>: <span className="value">{PROBLEM_DATA.target}</span>
              {'\n'}<span className="bracket">{'}'}</span>
            </div>
          </div>
          <div className="col">
            <div style={{ fontWeight: 600, marginBottom: 6, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              📤 期望答案 (Expected Answer)
            </div>
            <div className="io-block">
              <span className="bracket">[</span><span className="value">1</span>, <span className="value">3</span><span className="bracket">]</span>
              {'\n\n'}
              <span style={{ color: '#94a3b8' }}>{'// nums[1]=2, nums[3]=6'}</span>
              {'\n'}<span style={{ color: '#94a3b8' }}>{'// 2+6=8 ✓'}</span>
            </div>
            {showAnswer && (
              <div style={{ marginTop: 12, padding: '10px 14px', background: 'var(--success-bg)', borderRadius: 'var(--radius-sm)', border: '1px solid #bbf7d0', fontSize: '0.9rem' }}>
                <strong>✅ 最终答案：</strong> [1, 3]，即价格为 2 和 6 的两件商品，总价 2 + 6 = 8 = target。
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Algorithm Visualization */}
      <div className="card">
        <div className="card-title"><span className="icon">🔬</span> 算法可视化</div>
        <AlgorithmVisualizer
          nums={PROBLEM_DATA.nums}
          target={PROBLEM_DATA.target}
          left={currState.left}
          right={currState.right}
          sum={currState.sum}
          foundIndices={found}
          step={currentStep}
          totalSteps={steps.length - 1}
          isComplete={isComplete}
        />

        {/* State bar */}
        <div className="state-bar">
          <div className="state-item">
            <span className="s-label">左指针:</span>
            <span className="s-value" style={{ color: 'var(--pointer-left)' }}>left={currState.left}</span>
          </div>
          <div className="state-item">
            <span className="s-label">右指针:</span>
            <span className="s-value" style={{ color: 'var(--pointer-right)' }}>right={currState.right}</span>
          </div>
          <div className="state-item">
            <span className="s-label">当前和:</span>
            <span className="s-value">
              nums[{currState.left}]+nums[{currState.right}] = {PROBLEM_DATA.nums[currState.left]} + {PROBLEM_DATA.nums[currState.right]} = <strong>{currState.sum}</strong>
            </span>
          </div>
          <div className="state-item">
            <span className="s-label">target:</span>
            <span className="s-value">{PROBLEM_DATA.target}</span>
          </div>
          <div className="state-item">
            <span className="s-label">比较:</span>
            <span className="s-value" style={{ color: sumCompareColor }}>
              {sumCompareResult}
            </span>
          </div>
        </div>

        {/* Hint */}
        {showHint && (
          <div className="hint-box">
            <strong>💡 提示：</strong> 根据当前两数之和与 target 的关系决定指针移动方向。
            如果 <code>{'sum < target'}</code>，左指针右移以增大 sum；
            如果 <code>{'sum > target'}</code>，右指针左移以减小 sum；
            如果 <code>{'sum = target'}</code>，找到答案！左指针从 0 开始，右指针从末尾开始，逐步收缩搜索区间。
          </div>
        )}

        {/* Controls */}
        <div className="controls" style={{ marginTop: 16 }}>
          <span className="step-indicator">步骤 {currentStep} / {steps.length - 1}</span>
          <button className="btn" onClick={handleStepBackward} disabled={currentStep <= 0}>
            ◀ 上一步
          </button>
          <button className="btn primary" onClick={handleStepForward} disabled={isComplete}>
            下一步 ▶
          </button>
          <button className="btn" onClick={handleAutoPlay} disabled={isComplete && !autoPlaying}>
            {autoPlaying ? '⏸ 停止' : '▶ 自动播放'}
          </button>
          <button className="btn" onClick={handleReset}>
            🔄 重置
          </button>
          <button className="btn hint" onClick={handleHint} disabled={showHint}>
            💡 提示
          </button>
          <button className="btn answer" onClick={handleShowAnswer} disabled={showAnswer}>
            👁️ 显示答案
          </button>
        </div>
      </div>

      {/* Quiz Panel */}
      <div className="card">
        <div className="card-title"><span className="icon">🎯</span> 学习者预测练习</div>
        <QuizPanel
          state={currState}
          nums={PROBLEM_DATA.nums}
          target={PROBLEM_DATA.target}
          quizState={quizState}
          quizResult={quizResult}
          onStart={handleStartQuiz}
          onAnswer={handleQuizAnswer}
          isComplete={isComplete}
        />
      </div>

      {/* Activity Log */}
      <div className="card">
        <div className="card-title"><span className="icon">📜</span> 学习活动记录</div>
        <ActivityLog entries={logEntries} />
      </div>
    </div>
  );
}