import { useState, useCallback, useRef, useEffect } from 'react';
import { StepData, LogEntry } from './types';
import {
  generateSteps,
  getFinalAnswer,
  PROBLEM_INPUT,
  QUIZ_QUESTIONS,
} from './algorithm';
import './App.css';

const ALL_STEPS = generateSteps(PROBLEM_INPUT);
const FINAL_ANSWER = getFinalAnswer(PROBLEM_INPUT);

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function getActionLabel(action: StepData['action']): string {
  switch (action) {
    case 'push':
      return '直接加入';
    case 'push-and-pop':
      return '弹出后加入';
    case 'ignore':
      return '忽略';
  }
}

function getActionClass(action: StepData['action']): string {
  return action;
}

export default function App() {
  const [currentStepIdx, setCurrentStepIdx] = useState(-1);
  const [activityLog, setActivityLog] = useState<LogEntry[]>([]);
  const [autoPlaying, setAutoPlaying] = useState(false);
  const [quizStates, setQuizStates] = useState<
    Record<number, {
      selected: string | null;
      revealed: boolean;
      hintShown: boolean;
      locked: boolean;
    }>
  >({});
  const autoTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const logIdRef = useRef(0);

  const addLog = useCallback(
    (
      type: LogEntry['type'],
      detail: string,
      isCorrect?: boolean
    ) => {
      logIdRef.current += 1;
      const entry: LogEntry = {
        id: logIdRef.current,
        timestamp: Date.now(),
        type,
        detail,
        isCorrect,
      };
      setActivityLog((prev) => [entry, ...prev].slice(0, 60));
    },
    []
  );

  const goToStep = useCallback(
    (idx: number) => {
      const clamped = Math.max(-1, Math.min(ALL_STEPS.length - 1, idx));
      setCurrentStepIdx(clamped);
      if (clamped >= 0) {
        const s = ALL_STEPS[clamped];
        addLog(
          'step-nav',
          `步骤 ${clamped + 1}/${ALL_STEPS.length}: 处理元素 ${s.element} → ${getActionLabel(s.action)}`
        );
      }
    },
    [addLog]
  );

  const reset = useCallback(() => {
    setCurrentStepIdx(-1);
    setQuizStates({});
    setAutoPlaying(false);
    if (autoTimerRef.current) {
      clearInterval(autoTimerRef.current);
      autoTimerRef.current = null;
    }
    addLog('reset', '已重置所有状态');
  }, [addLog]);

  const toggleAutoPlay = useCallback(() => {
    setAutoPlaying((prev) => {
      if (prev) {
        if (autoTimerRef.current) {
          clearInterval(autoTimerRef.current);
          autoTimerRef.current = null;
        }
        addLog('auto-play', '自动播放已停止');
        return false;
      } else {
        addLog('auto-play', '自动播放已开始');
        return true;
      }
    });
  }, [addLog]);

  useEffect(() => {
    if (autoPlaying) {
      autoTimerRef.current = setInterval(() => {
        setCurrentStepIdx((prev) => {
          const next = prev + 1;
          if (next >= ALL_STEPS.length) {
            setAutoPlaying(false);
            if (autoTimerRef.current) {
              clearInterval(autoTimerRef.current);
              autoTimerRef.current = null;
            }
            return prev;
          }
          const s = ALL_STEPS[next];
          logIdRef.current += 1;
          setActivityLog((lg) =>
            [
              {
                id: logIdRef.current,
                timestamp: Date.now(),
                type: 'step-nav' as const,
                detail: `步骤 ${next + 1}/${ALL_STEPS.length}: 处理元素 ${s.element} → ${getActionLabel(s.action)}`,
              },
              ...lg,
            ].slice(0, 60)
          );
          return next;
        });
      }, 1200);
      return () => {
        if (autoTimerRef.current) {
          clearInterval(autoTimerRef.current);
          autoTimerRef.current = null;
        }
      };
    }
  }, [autoPlaying]);

  useEffect(() => {
    return () => {
      if (autoTimerRef.current) clearInterval(autoTimerRef.current);
    };
  }, []);

  const currentStep: StepData | null =
    currentStepIdx >= 0 ? ALL_STEPS[currentStepIdx] : null;

  function handleQuizSelect(qId: number, option: string) {
    const q = QUIZ_QUESTIONS.find((x) => x.id === qId)!;
    const current = quizStates[qId];
    if (current?.locked) return;
    const isCorrect = option === q.correctAnswer;
    setQuizStates((prev) => ({
      ...prev,
      [qId]: { ...prev[qId], selected: option, revealed: true, locked: true, hintShown: prev[qId]?.hintShown ?? false },
    }));
    addLog(
      'quiz-attempt',
      `问题 ${qId}: 选择 "${option}" — ${isCorrect ? '✓ 正确' : '✗ 错误'}`,
      isCorrect
    );
  }

  function handleHint(qId: number) {
    setQuizStates((prev) => ({
      ...prev,
      [qId]: { ...prev[qId], hintShown: true },
    }));
    addLog('hint-request', `问题 ${qId}: 请求提示`);
  }

  function handleShowAnswer(qId: number) {
    const q = QUIZ_QUESTIONS.find((x) => x.id === qId)!;
    setQuizStates((prev) => ({
      ...prev,
      [qId]: {
        ...prev[qId],
        selected: q.correctAnswer,
        revealed: true,
        locked: true,
        hintShown: true,
      },
    }));
    addLog('show-answer', `问题 ${qId}: 查看答案 → "${q.correctAnswer}"`);
  }

  function renderHeapCells(
    heap: number[],
    highlightVal: number | null,
    highlightType: 'push' | 'pop' | null,
    topVal: number | null
  ) {
    if (heap.length === 0) {
      return <div className="heap-empty">空</div>;
    }
    return (
      <div className="heap-boxes">
        {heap.map((v, i) => {
          const isTop = topVal !== null && v === topVal && i === 0;
          const isHighlighted = highlightVal !== null && v === highlightVal;
          let cls = 'normal';
          if (isHighlighted && highlightType === 'push') cls = 'highlight-push';
          if (isHighlighted && highlightType === 'pop') cls = 'highlight-pop';
          return (
            <div
              key={i}
              className={`heap-cell ${cls} ${isTop ? 'heap-top' : ''}`}
              title={isTop ? `堆顶 (第${PROBLEM_INPUT.k}大): ${v}` : `索引 ${i}: ${v}`}
            >
              {v}
              <span className="cell-index">[{i}]</span>
              {isTop && <span className="top-marker">←堆顶</span>}
            </div>
          );
        })}
      </div>
    );
  }

  function renderElementStrip() {
    return (
      <div className="element-strip">
        <span className="element-strip-label">数组:</span>
        {PROBLEM_INPUT.nums.map((v, i) => {
          let cls = 'pending';
          let label = '';
          if (currentStepIdx >= 0) {
            if (i < currentStepIdx) { cls = 'processed'; label = '已处理'; }
            else if (i === currentStepIdx) { cls = 'current'; label = '当前'; }
            else { cls = 'pending'; label = '待处理'; }
          }
          return (
            <div key={i} className={`element-chip ${cls}`} title={`索引 ${i}: ${v} (${label})`}>
              {v}
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="badge">堆 / TopK / Huffman</div>
        <h1>数组中的第 K 个最大元素</h1>
        <p className="subtitle">
          使用容量为 k 的小顶堆，流式处理评分数据，实时查询第 K 高评分
        </p>
      </header>

      <div className="content-layout">
        {/* Main Column */}
        <div className="main-column">
          {/* Problem Description */}
          <div className="card">
            <div className="card-header">
              <span className="icon">📖</span> 问题描述
            </div>
            <div className="problem-text">
              <p>
                某个推荐系统需要从用户评分流中找出前 <strong>K</strong> 个高评分商品。
                评分数据存储在一个数组 <code>nums</code> 中，整数 <code>k</code> 表示需要的第 K 个最高评分。
                请实现一个流式算法，当逐个处理 nums 中的评分时，随时能查询当前第 K 高的评分，
                并在所有数据处理完毕后返回最终的第 K 高评分。
              </p>
              <div className="strategy-box">
                <strong>策略：</strong>维护容量为 k 的小顶堆，堆顶即为当前第 K 大元素。
              </div>
            </div>
          </div>

          {/* Input / Output */}
          <div className="io-row">
            <div className="io-card input-card">
              <div className="io-label">📥 输入 (JSON)</div>
              <div className="io-value">
                k = {PROBLEM_INPUT.k}, nums = [{PROBLEM_INPUT.nums.join(', ')}]
              </div>
            </div>
            <div className="io-card output-card">
              <div className="io-label">📤 最终答案</div>
              <div className="io-value">{FINAL_ANSWER}</div>
            </div>
          </div>

          {/* Visualization */}
          <div className="viz-container">
            <div className="viz-title">
              🔍 算法过程可视化
              <span className="step-indicator">
                {currentStep
                  ? `步骤 ${currentStepIdx + 1} / ${ALL_STEPS.length}`
                  : '点击下方按钮开始'}
              </span>
            </div>

            {/* Element strip */}
            {renderElementStrip()}

            {/* Step navigation */}
            <div className="step-controls" style={{ marginBottom: 16 }}>
              <button
                className="btn-outline"
                disabled={currentStepIdx < 0}
                onClick={() => goToStep(-1)}
                title="回到初始状态"
              >
                ⏮ 重置
              </button>
              <button
                className="btn-primary"
                disabled={currentStepIdx <= -1}
                onClick={() => goToStep(currentStepIdx - 1)}
                title="查看上一步"
              >
                ◀ 上一步
              </button>
              <button
                className="btn-primary"
                disabled={currentStepIdx >= ALL_STEPS.length - 1}
                onClick={() => goToStep(currentStepIdx + 1)}
                title="查看下一步"
              >
                下一步 ▶
              </button>
              <button
                className={`btn-auto ${autoPlaying ? 'playing' : ''}`}
                disabled={currentStepIdx >= ALL_STEPS.length - 1 && !autoPlaying}
                onClick={toggleAutoPlay}
                title={autoPlaying ? '暂停自动播放' : '自动逐步演示'}
              >
                {autoPlaying ? '⏸ 停止' : '▶ 自动播放'}
              </button>
              <div className="step-dots" title="点击圆点直接跳转到对应步骤">
                {ALL_STEPS.map((_, i) => (
                  <button
                    key={i}
                    className={`step-dot ${i === currentStepIdx ? 'active' : ''}`}
                    onClick={() => goToStep(i)}
                    title={`跳转到步骤 ${i + 1}`}
                    aria-label={`步骤 ${i + 1}`}
                  />
                ))}
              </div>
            </div>

            {/* Current step detail */}
            {currentStep ? (
              <div className="animate-in">
                <div className="element-flow">
                  <div className="current-element-box" title="正在处理的当前元素">
                    <div className="ce-label">当前元素</div>
                    <div className="ce-value">{currentStep.element}</div>
                  </div>
                  <span
                    className={`action-badge ${getActionClass(currentStep.action)}`}
                    title={getActionLabel(currentStep.action)}
                  >
                    {getActionLabel(currentStep.action)}
                  </span>
                </div>
                <div className="description-text">{currentStep.description}</div>
                <div className="heap-display-row">
                  <div className="heap-panel">
                    <div className="heap-panel-label">处理前堆</div>
                    {renderHeapCells(
                      currentStep.heapBefore,
                      currentStep.action === 'push-and-pop'
                        ? currentStep.heapBefore[0]
                        : null,
                      currentStep.action === 'push-and-pop' ? 'pop' : null,
                      null
                    )}
                  </div>
                  <div className="heap-panel">
                    <div className="heap-panel-label">处理后堆</div>
                    {renderHeapCells(
                      currentStep.heapAfter,
                      currentStep.element,
                      currentStep.action === 'ignore' ? null : 'push',
                      currentStep.heapTop
                    )}
                    {currentStep.heapTop !== null && (
                      <div className="heap-top-indicator">
                        堆顶 = {currentStep.heapTop}（当前第 {PROBLEM_INPUT.k} 大）
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="animate-in" style={{ textAlign: 'center', padding: '40px 20px', color: '#94a3b8' }}>
                <div style={{ fontSize: '2.5rem', marginBottom: 10 }}>📊</div>
                <p>点击 <strong>"下一步"</strong> 或 <strong>"自动播放"</strong> 开始查看算法执行过程</p>
                <p style={{ fontSize: '0.8rem', marginTop: 6 }}>
                  小顶堆将逐步处理每个评分，维护前 K 大元素
                </p>
              </div>
            )}
          </div>

          {/* Quiz Panel */}
          <div className="quiz-card">
            <div className="quiz-title">📝 学习检查点</div>
            {QUIZ_QUESTIONS.map((q) => {
              const qs = quizStates[q.id] || {
                selected: null,
                revealed: false,
                hintShown: false,
                locked: false,
              };
              const isCorrect = qs.selected === q.correctAnswer;
              const isWrong = qs.revealed && !isCorrect;

              return (
                <div
                  key={q.id}
                  className={`quiz-item ${isCorrect && qs.revealed ? 'correct-flash' : ''} ${isWrong ? 'incorrect-flash' : ''}`}
                >
                  <div className="quiz-question-text">
                    <strong>问题 {q.id}：</strong>
                    {q.question}
                  </div>
                  <div className="quiz-options">
                    {q.options.map((opt, oi) => {
                      let optCls = '';
                      if (qs.revealed) {
                        if (opt === q.correctAnswer) optCls = 'correct-choice';
                        else if (opt === qs.selected && !isCorrect)
                          optCls = 'wrong-choice';
                      } else if (qs.selected === opt) {
                        optCls = 'selected';
                      }
                      return (
                        <div
                          key={oi}
                          className={`quiz-option ${optCls}`}
                          onClick={() => handleQuizSelect(q.id, opt)}
                          title={qs.revealed ? '' : `选择: ${opt}`}
                        >
                          <span
                            style={{
                              width: 18,
                              height: 18,
                              borderRadius: '50%',
                              border: '2px solid #cbd5e1',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '0.65rem',
                              flexShrink: 0,
                              ...(optCls === 'correct-choice'
                                ? {
                                    borderColor: '#22c55e',
                                    background: '#22c55e',
                                    color: '#fff',
                                  }
                                : {}),
                              ...(optCls === 'wrong-choice'
                                ? {
                                    borderColor: '#ef4444',
                                    background: '#ef4444',
                                    color: '#fff',
                                  }
                                : {}),
                              ...(optCls === 'selected' && !qs.revealed
                                ? { borderColor: '#3b82f6', background: '#3b82f6', color: '#fff' }
                                : {}),
                            }}
                          >
                            {optCls === 'correct-choice'
                              ? '✓'
                              : optCls === 'wrong-choice'
                                ? '✗'
                                : String.fromCharCode(65 + oi)}
                          </span>
                          {opt}
                        </div>
                      );
                    })}
                  </div>

                  {qs.revealed && (
                    <div
                      className={`quiz-feedback ${isCorrect ? 'correct' : 'incorrect'}`}
                    >
                      {isCorrect ? '✅ 回答正确！' : '❌ 回答错误。'}{' '}
                      {q.explanation}
                    </div>
                  )}

                  {qs.hintShown && !qs.revealed && (
                    <div className="hint-text">💡 {q.hint}</div>
                  )}

                  <div className="quiz-actions">
                    {!qs.revealed && (
                      <button
                        className="btn-hint"
                        onClick={() => handleHint(q.id)}
                        title="显示解题提示"
                      >
                        💡 提示
                      </button>
                    )}
                    {!qs.revealed && (
                      <button
                        className="btn-show-answer"
                        onClick={() => handleShowAnswer(q.id)}
                        title="直接查看正确答案"
                      >
                        🔑 查看答案
                      </button>
                    )}
                    {qs.revealed && (
                      <span
                        style={{
                          fontSize: '0.78rem',
                          color: isCorrect ? '#166534' : '#991b1b',
                          fontWeight: 600,
                        }}
                      >
                        {isCorrect ? '✓ 已完成' : '✗ 已查看答案'}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Learning Objectives */}
          <div className="card">
            <div className="card-header">
              <span className="icon">🎯</span> 学习目标
            </div>
            <ul className="objectives-list">
              <li>理解小顶堆在 TopK 问题中如何维护状态，解释为什么堆顶是第 K 大元素</li>
              <li>能够根据当前堆状态预测下一个元素加入后的堆变化</li>
              <li>掌握堆的 push 和 pop 操作对候选集大小和堆顶的影响</li>
            </ul>
          </div>
        </div>

        {/* Sidebar */}
        <div className="sidebar">
          {/* Activity Log */}
          <div className="activity-log">
            <div className="activity-log-header">
              📋 学习活动记录
              <button
                className="btn-ghost"
                style={{ fontSize: '0.7rem', padding: '3px 8px' }}
                onClick={reset}
                title="重置算法步骤与测验进度"
              >
                重置全部
              </button>
            </div>
            <div className="activity-log-list">
              {activityLog.length === 0 ? (
                <div className="activity-empty-state">
                  <div className="activity-empty-icon">📝</div>
                  <div className="activity-empty-title">还没有活动记录</div>
                  <div className="activity-empty-desc">
                    开始交互后，每一步操作都会实时显示在这里
                  </div>
                  <div className="activity-empty-hints">
                    <div className="activity-empty-hint">
                      <span className="dot-icon blue" /> 点击导航按钮查看算法步骤
                    </div>
                    <div className="activity-empty-hint">
                      <span className="dot-icon green" /> 回答下方学习检查点问题
                    </div>
                    <div className="activity-empty-hint">
                      <span className="dot-icon amber" /> 使用提示功能获取帮助
                    </div>
                    <div className="activity-empty-hint">
                      <span className="dot-icon red" /> 查看答案学习正确解法
                    </div>
                  </div>
                </div>
              ) : (
                activityLog.map((entry) => {
                  const iconMap: Record<string, string> = {
                    'step-nav': '→',
                    'quiz-attempt': entry.isCorrect ? '✓' : '✗',
                    'hint-request': '?',
                    'show-answer': '!',
                    reset: '↺',
                    'auto-play': '▶',
                  };
                  const iconCls = `${entry.type} ${entry.type === 'quiz-attempt' && entry.isCorrect === false ? 'incorrect' : ''}`;
                  return (
                    <div key={entry.id} className="log-entry">
                      <div className={`log-icon ${iconCls}`}>
                        {iconMap[entry.type] || '•'}
                      </div>
                      <div className="log-detail">{entry.detail}</div>
                      <div className="log-time">{formatTime(entry.timestamp)}</div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}