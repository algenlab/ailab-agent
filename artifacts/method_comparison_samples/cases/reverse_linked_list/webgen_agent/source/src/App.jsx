import React, { useState, useCallback, useRef, useEffect } from 'react';

/* ============================================================
   Data & Algorithm Logic
   ============================================================ */
const INITIAL_VALUES = [1, 2, 3];
const FINAL_ANSWER = [3, 2, 1];

// Each step in the algorithm trace
function buildTrace(values) {
  const steps = [];
  let prev = null;
  let curr = 0;
  let next = 1;

  const nodes = values.map((v, i) => ({
    id: i,
    val: v,
    next: i + 1 < values.length ? i + 1 : null,
  }));

  // Step 0: initial state
  steps.push({
    stepNum: 0,
    phase: 'initial',
    description: '初始状态：链表按原始顺序连接，prev=null，curr 指向第一个节点，next 指向第二个节点。尚未开始反转。',
    prev: null,
    curr: 0,
    next: 1,
    nodes: JSON.parse(JSON.stringify(nodes)),
    operation: null,
  });

  let localPrev = null;
  let localCurr = 0;
  let localNext = 1;
  const mutableNodes = JSON.parse(JSON.stringify(nodes));

  let stepNum = 1;

  while (localCurr !== null) {
    const savedNext = localNext;

    // Step: reverse pointer
    steps.push({
      stepNum: stepNum++,
      phase: 'reverse',
      description: `操作 curr.next = prev：将节点 ${mutableNodes[localCurr].val} 的 next 指针从指向 ${
        mutableNodes[localCurr].next !== null ? '节点 ' + mutableNodes[mutableNodes[localCurr].next].val : 'null'
      } 改为指向 ${
        localPrev !== null ? '节点 ' + mutableNodes[localPrev].val : 'null'
      }。`,
      prev: localPrev,
      curr: localCurr,
      next: localNext,
      nodes: JSON.parse(JSON.stringify(mutableNodes)),
      operation: 'curr.next = prev',
      operationDetail: {
        node: mutableNodes[localCurr].val,
        from: mutableNodes[localCurr].next !== null ? mutableNodes[mutableNodes[localCurr].next].val : null,
        to: localPrev !== null ? mutableNodes[localPrev].val : null,
      },
    });

    // Perform reversal on our mutable copy
    mutableNodes[localCurr].next = localPrev;

    // Step: advance pointers
    steps.push({
      stepNum: stepNum++,
      phase: 'advance',
      description: `指针前移：prev 移动到 curr（节点 ${mutableNodes[localCurr].val}），curr 移动到 next（${
        savedNext !== null ? '节点 ' + mutableNodes[savedNext].val : 'null'
      }）${savedNext !== null && savedNext + 1 < values.length ? '，next 移动到节点 ' + mutableNodes[savedNext + 1].val : savedNext !== null ? '，next 变为 null' : ''}。`,
      prev: localCurr,
      curr: savedNext,
      next: savedNext !== null ? (savedNext + 1 < values.length ? savedNext + 1 : null) : null,
      nodes: JSON.parse(JSON.stringify(mutableNodes)),
      operation: 'prev = curr; curr = next; next = next?.next',
      operationDetail: {
        prevMovesTo: mutableNodes[localCurr].val,
        currMovesTo: savedNext !== null ? mutableNodes[savedNext].val : null,
      },
    });

    // Advance
    localPrev = localCurr;
    localCurr = savedNext;
    localNext = savedNext !== null ? (savedNext + 1 < values.length ? savedNext + 1 : null) : null;

    if (localCurr === null) {
      steps.push({
        stepNum: stepNum++,
        phase: 'complete',
        description: `反转完成！prev 现在指向原链表的尾节点（新头节点 ${mutableNodes[localPrev].val}），curr 为 null。链表已完全反转，新顺序为 [${values.slice().reverse().join(', ')}]。`,
        prev: localPrev,
        curr: null,
        next: null,
        nodes: JSON.parse(JSON.stringify(mutableNodes)),
        operation: null,
      });
    }
  }

  return steps;
}

/* ============================================================
   Phase label helper
   ============================================================ */
function phaseLabel(phase) {
  switch (phase) {
    case 'initial': return '初始状态';
    case 'reverse': return '反转指针';
    case 'advance': return '移动指针';
    case 'complete': return '完成';
    default: return phase;
  }
}

/* ============================================================
   Components
   ============================================================ */

// Single node display
function ListNode({ val, isCurr, isPrev, isNext, nextPointsTo }) {
  let cls = 'node';
  if (isCurr) cls += ' curr';
  else if (isPrev) cls += ' prev-highlight';
  else if (isNext) cls += ' next-highlight';

  return (
    <div className="node" title={`值: ${val}${nextPointsTo !== undefined ? ', next→' + (nextPointsTo ?? 'null') : ''}`}>
      {val}
    </div>
  );
}

// Arrow between nodes
function Arrow({ reversed }) {
  return (
    <div className={'arrow-connector' + (reversed ? ' reversed' : '')}>
      <svg viewBox="0 0 44 20">
        {reversed ? (
          <line x1="4" y1="10" x2="40" y2="10" stroke="#f59e0b" strokeWidth="2.5" markerEnd="url(#ah-rev)" />
        ) : (
          <line x1="4" y1="10" x2="40" y2="10" stroke="#94a3b8" strokeWidth="2.5" markerEnd="url(#ah)" />
        )}
      </svg>
    </div>
  );
}

// SVG defs for arrows
function ArrowDefs() {
  return (
    <svg width="0" height="0" style={{ position: 'absolute' }}>
      <defs>
        <marker id="ah" markerWidth="7" markerHeight="5" refX="7" refY="2.5" orient="auto">
          <polygon points="0 0, 7 2.5, 0 5" fill="#94a3b8" />
        </marker>
        <marker id="ah-rev" markerWidth="7" markerHeight="5" refX="0" refY="2.5" orient="auto">
          <polygon points="7 0, 0 2.5, 7 5" fill="#f59e0b" />
        </marker>
      </defs>
    </svg>
  );
}

// Visualization of the linked list at a given step
function LinkedListViz({ step }) {
  const { nodes, prev, curr, next: nextIdx } = step;

  return (
    <div className="viz-stage">
      <ArrowDefs />
      {nodes.map((node, i) => (
        <React.Fragment key={i}>
          {i > 0 && (
            <Arrow reversed={nodes[i - 1].next === i && nodes[i].next === i - 1} />
          )}
          <ListNode
            val={node.val}
            isCurr={curr === i}
            isPrev={prev === i}
            isNext={nextIdx === i}
            nextPointsTo={node.next !== null ? nodes[node.next]?.val : null}
          />
        </React.Fragment>
      ))}
    </div>
  );
}

// Pointer labels below the visualization
function PointerLabels({ step }) {
  const { prev, curr, next: nextIdx, nodes } = step;
  if (!nodes || nodes.length === 0) return null;

  return (
    <div className="ptr-labels">
      {nodes.map((node, i) => (
        <React.Fragment key={i}>
          {i > 0 && <div className="ptr-label-spacer" style={{ width: 44 }} />}
          <div style={{ width: 62, textAlign: 'center' }}>
            {prev === i && <span className="ptr-label prev">prev</span>}
            {curr === i && <span className="ptr-label curr">curr</span>}
            {nextIdx === i && <span className="ptr-label next">next</span>}
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}

// Legend for pointer colors
function Legend() {
  return (
    <div className="legend-row">
      <div className="legend-item"><div className="legend-dot cdot" /> curr（当前节点）</div>
      <div className="legend-item"><div className="legend-dot pdot" /> prev（前驱节点）</div>
      <div className="legend-item"><div className="legend-dot ndot" /> next（后继节点）</div>
      <div className="legend-item"><div className="legend-dot rdot" /> 普通节点</div>
    </div>
  );
}

// Target (final reversed list) display
function TargetDisplay({ values }) {
  const reversed = [...values].reverse();
  return (
    <div className="target-section">
      {reversed.map((v, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span className="target-arrow">→</span>}
          <div className="target-node">{v}</div>
        </React.Fragment>
      ))}
    </div>
  );
}

// Checkpoint questions
const QUESTIONS = [
  {
    id: 'q1',
    text: '当前 trace 中 curr 指向值为 2 的节点，prev 指向值为 1 的节点，next 指向值为 3 的节点。请预测下一步 curr.next 会指向哪个值？',
    options: ['1', '2', '3', 'null'],
    correct: 0,
  },
  {
    id: 'q2',
    text: '在反转链表的迭代过程中，无论哪一步，哪个语句始终是真？请从 trace 中找出一个不变量。',
    options: [
      'curr 永远不为 null',
      'prev 和 curr 之间的边已经反转',
      '所有节点都保持原值不变',
      'next 指针始终指向 curr',
    ],
    correct: 1,
  },
  {
    id: 'q3',
    text: '原 values 为 [1,2,3]，反转后为 [3,2,1]。如果删除中间节点 2，删除后反转结果是什么？',
    options: ['[3, 1]', '[1, 3]', '[3, 2, 1]', '[1, 2]'],
    correct: 0,
  },
  {
    id: 'q4',
    text: '在步骤 2，trace 显示操作 \'curr.next = prev\'。请解释这一步的目的。',
    options: [
      '将当前节点指向下一个节点',
      '将当前节点的 next 指针反转指向前一个节点',
      '将 prev 指针移动到 curr',
      '删除当前节点',
    ],
    correct: 1,
  },
];

/* ============================================================
   Main App
   ============================================================ */
export default function App() {
  const [values] = useState(INITIAL_VALUES);
  const [trace] = useState(() => buildTrace(INITIAL_VALUES));
  const [stepIdx, setStepIdx] = useState(0);
  const [autoPlaying, setAutoPlaying] = useState(false);
  const [speed, setSpeed] = useState(1200);
  const [showHint, setShowHint] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);
  const [log, setLog] = useState([]);
  const [questionIdx, setQuestionIdx] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [qFeedback, setQFeedback] = useState(null);
  const [qLocked, setQLocked] = useState(false);

  const autoTimerRef = useRef(null);
  const logIdRef = useRef(0);

  const currentStep = trace[stepIdx];
  const isLastStep = stepIdx === trace.length - 1;
  const isFirstStep = stepIdx === 0;
  const totalSteps = trace.length;
  const maxStepNum = trace[totalSteps - 1].stepNum;
  const progressPercent = maxStepNum > 0 ? Math.round((currentStep.stepNum / maxStepNum) * 100) : 0;

  const addLog = useCallback((msg) => {
    const now = new Date();
    const time = now.toLocaleTimeString('zh-CN', { hour12: false });
    setLog((prev) => {
      const next = [...prev, { id: ++logIdRef.current, time, msg }];
      return next.length > 50 ? next.slice(-50) : next;
    });
  }, []);

  // Auto-play
  useEffect(() => {
    if (autoPlaying && !isLastStep) {
      autoTimerRef.current = setTimeout(() => {
        setStepIdx((s) => Math.min(s + 1, trace.length - 1));
      }, speed);
    } else if (autoPlaying && isLastStep) {
      setAutoPlaying(false);
      addLog('⏹ 自动播放结束，已到达最后一步');
    }
    return () => clearTimeout(autoTimerRef.current);
  }, [autoPlaying, stepIdx, isLastStep, speed, trace.length, addLog]);

  const goNext = useCallback(() => {
    if (!isLastStep) {
      const nextIdx = stepIdx + 1;
      setStepIdx(nextIdx);
      addLog(`▶ 进入步骤 ${trace[nextIdx].stepNum}：${phaseLabel(trace[nextIdx].phase)}`);
    }
  }, [isLastStep, stepIdx, trace, addLog]);

  const goPrev = useCallback(() => {
    if (!isFirstStep) {
      const prevIdx = stepIdx - 1;
      setStepIdx(prevIdx);
      addLog(`◀ 回到步骤 ${trace[prevIdx].stepNum}：${phaseLabel(trace[prevIdx].phase)}`);
    }
  }, [isFirstStep, stepIdx, trace, addLog]);

  const goReset = useCallback(() => {
    setStepIdx(0);
    setAutoPlaying(false);
    addLog('🔄 重置到初始状态（步骤 0）');
  }, [addLog]);

  const toggleAuto = useCallback(() => {
    setAutoPlaying((p) => {
      const next = !p;
      addLog(next ? '▶ 开始自动播放' : '⏸ 暂停自动播放');
      return next;
    });
  }, [addLog]);

  // Hint
  const handleHint = useCallback(() => {
    setShowHint((prev) => !prev);
    if (!showHint) {
      addLog('💡 显示提示信息');
    } else {
      addLog('💡 隐藏提示信息');
    }
  }, [showHint, addLog]);

  const handleShowAnswer = useCallback(() => {
    setShowAnswer(true);
    setStepIdx(trace.length - 1);
    setAutoPlaying(false);
    addLog('🔍 跳转到最终答案（步骤 ' + trace[trace.length - 1].stepNum + '）');
  }, [trace, addLog]);

  // Question
  const currentQ = QUESTIONS[questionIdx];

  const handleOptionSelect = useCallback(
    (idx) => {
      if (qLocked) return;
      setSelectedOption(idx);
      setQLocked(true);
      const isCorrect = idx === currentQ.correct;
      setQFeedback(isCorrect ? 'correct' : 'wrong');
      addLog(
        isCorrect
          ? `✅ 问题 ${questionIdx + 1} 回答正确：选择了 "${currentQ.options[idx]}"`
          : `❌ 问题 ${questionIdx + 1} 回答错误：选择了 "${currentQ.options[idx]}"，正确答案是 "${currentQ.options[currentQ.correct]}"`
      );
    },
    [qLocked, currentQ, addLog, questionIdx]
  );

  const nextQuestion = useCallback(() => {
    if (questionIdx < QUESTIONS.length - 1) {
      setQuestionIdx((q) => q + 1);
      setSelectedOption(null);
      setQFeedback(null);
      setQLocked(false);
      addLog('📋 切换到题目 ' + (questionIdx + 2));
    }
  }, [questionIdx, addLog]);

  const prevQuestion = useCallback(() => {
    if (questionIdx > 0) {
      setQuestionIdx((q) => q - 1);
      setSelectedOption(null);
      setQFeedback(null);
      setQLocked(false);
      addLog('📋 切换到题目 ' + questionIdx);
    }
  }, [questionIdx, addLog]);

  // Initial log
  useEffect(() => {
    addLog('📖 页面加载完成，准备学习反转链表算法');
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <h1>🔗 反转链表</h1>
        <span className="family-tag">链表与缓存</span>
      </header>

      {/* Breadcrumb */}
      <nav className="breadcrumb">
        <span>🏠 首页</span><span className="breadcrumb-sep">›</span>
        <span>📚 算法学习</span><span className="breadcrumb-sep">›</span>
        <span>链表与缓存</span><span className="breadcrumb-sep">›</span>
        <span className="active">反转链表</span>
      </nav>

      {/* Problem Description */}
      <div className="card">
        <h2>📝 问题描述</h2>
        <p style={{ fontSize: '0.92rem', color: 'var(--text-muted)', lineHeight: 1.8 }}>
          假设你正在开发一个浏览器，用户访问了一系列网页，用一个列表 <code>values</code> 记录访问的网址ID。
          浏览器需要生成<strong>后退历史路径</strong>，即把访问顺序反转，使得用户可以从当前页逐步回到最早访问的页。
          给定列表 <code>values</code>，按顺序表示访问的网页ID，请实现算法返回反转后的列表，即后退的顺序。
        </p>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: 8 }}>
          <strong>参考策略：</strong>维护 <code>prev</code> / <code>curr</code> / <code>next</code>，逐个把 <code>curr.next</code> 指向 <code>prev</code>。
        </p>
      </div>

      {/* Input / Output */}
      <div className="card">
        <h2>📥 输入 / 📤 输出</h2>
        <div className="io-grid">
          <div className="io-box input">
            <label>输入 (Input)</label>
            <code>{`{ "values": [${values.join(', ')}] }`}</code>
          </div>
          <div className="io-box output">
            <label>期望输出 (Expected Output)</label>
            <code>{`[${FINAL_ANSWER.join(', ')}]`}</code>
          </div>
        </div>
      </div>

      {/* Visualization */}
      <div className="card">
        <h2>🎬 算法可视化</h2>

        {/* Progress bar */}
        <div className="progress-bar-wrap">
          <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }} />
        </div>

        <div className="step-indicator">
          步骤 <span>{currentStep.stepNum}</span> / {maxStepNum}
          <span className="badge info" style={{ marginLeft: 6 }}>
            {phaseLabel(currentStep.phase)}
          </span>
          {currentStep.operation && (
            <code className="op-detail">{currentStep.operation}</code>
          )}
        </div>
        <div className="step-description">{currentStep.description}</div>

        <Legend />
        <LinkedListViz step={currentStep} />
        <PointerLabels step={currentStep} />

        {/* Controls */}
        <div className="controls-row" style={{ marginTop: 18 }}>
          <button className="btn" onClick={goReset} disabled={isFirstStep && !autoPlaying}>
            ⏮ 重置
          </button>
          <button className="btn" onClick={goPrev} disabled={isFirstStep || autoPlaying}>
            ◀ 上一步
          </button>
          <button className="btn primary" onClick={goNext} disabled={isLastStep || autoPlaying}>
            下一步 ▶
          </button>
          <button className="btn accent" onClick={toggleAuto}>
            {autoPlaying ? '⏸ 暂停' : '▶ 自动播放'}
          </button>
        </div>
        <div className="controls-row" style={{ marginTop: 10 }}>
          <label style={{ fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: 6 }}>
            播放速度:
            <input
              type="range"
              className="speed-slider"
              min="400"
              max="2500"
              step="100"
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
            />
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{speed}ms</span>
          </label>
        </div>

        {/* Target at completion */}
        {currentStep.phase === 'complete' && (
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <span className="badge ok" style={{ fontSize: '0.82rem', padding: '6px 14px' }}>
              ✅ 反转完成！
            </span>
            <TargetDisplay values={values} />
          </div>
        )}
      </div>

      {/* Learner Questions */}
      <div className="card">
        <h2>🎯 学习检测 ({questionIdx + 1}/{QUESTIONS.length})</h2>
        <div className="question-card">
          <h3>{currentQ.text}</h3>
          <div className="options-row">
            {currentQ.options.map((opt, i) => {
              let optCls = 'option-btn';
              if (qLocked) {
                if (i === currentQ.correct) optCls += ' selected-correct';
                else if (i === selectedOption && selectedOption !== currentQ.correct) optCls += ' selected-wrong';
                optCls += ' locked';
              }
              return (
                <button
                  key={i}
                  className={optCls}
                  onClick={() => handleOptionSelect(i)}
                  disabled={qLocked}
                >
                  {opt}
                </button>
              );
            })}
          </div>
          {qFeedback && (
            <div className={`feedback-msg ${qFeedback}`}>
              {qFeedback === 'correct'
                ? '🎉 正确！回答得很好！'
                : `❌ 不正确。正确答案是：${currentQ.options[currentQ.correct]}`}
            </div>
          )}
          <div className="controls-row" style={{ marginTop: 12 }}>
            <button className="btn" onClick={prevQuestion} disabled={questionIdx === 0}>
              ◀ 上一题
            </button>
            <button className="btn" onClick={nextQuestion} disabled={questionIdx === QUESTIONS.length - 1}>
              下一题 ▶
            </button>
          </div>
        </div>

        {/* Hint + Show Answer */}
        <div className="controls-row" style={{ marginTop: 4 }}>
          <button className="btn warning" onClick={handleHint}>
            {showHint ? '🙈 隐藏提示' : '💡 显示提示'}
          </button>
          <button className="btn success" onClick={handleShowAnswer}>
            🔍 显示答案
          </button>
        </div>
        {showHint && (
          <div className="hint-box">
            <strong>💡 提示：</strong> 维护 <code>prev</code>、<code>curr</code>、<code>next</code> 三个指针，
            每次迭代中先保存 <code>next = curr.next</code>，再将 <code>curr.next</code> 指向 <code>prev</code>，
            最后将 <code>prev</code> 和 <code>curr</code> 同时前移一位。循环直到 <code>curr</code> 为 <code>null</code>，
            此时 <code>prev</code> 就是新链表的头节点。
          </div>
        )}
        {showAnswer && (
          <div className="hint-box" style={{ background: '#f0fdf4', borderColor: '#bbf7d0', color: '#15803d' }}>
            <strong>🔍 答案：</strong> 反转后的列表为 <code>[3, 2, 1]</code>。算法通过迭代反转每个节点的 next 指针实现，
            时间复杂度 O(n)，空间复杂度 O(1)。反转过程共 {maxStepNum} 个步骤（含初始状态）。
          </div>
        )}
      </div>

      {/* Learning Objectives */}
      <div className="card">
        <h2>📚 学习目标</h2>
        <ul style={{ paddingLeft: 20, fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.8 }}>
          <li>理解迭代反转单链表中 <code>prev</code>、<code>curr</code>、<code>next</code> 三个指针的状态变化</li>
          <li>根据 trace 预测下一步指针指向并解释原因</li>
          <li>识别反转过程中链表节点连接的不变式，并用于调试</li>
        </ul>
      </div>

      {/* Activity Log */}
      <div className="card">
        <h2>📜 活动日志</h2>
        <div className="log-area">
          {log.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>暂无活动记录</p>
          ) : (
            log.map((entry) => (
              <div key={entry.id} className="log-entry">
                <span className="log-time">[{entry.time}]</span>
                <span className="log-msg">{entry.msg}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}