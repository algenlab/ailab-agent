import React, { useState, useCallback, useEffect, useRef } from 'react';
import ProblemDisplay from './ProblemDisplay.jsx';
import DPTable from './DPTable.jsx';
import Controls from './Controls.jsx';
import Checkpoint from './Checkpoint.jsx';
import ActivityLog from './ActivityLog.jsx';
import { generateSteps, combinationPaths, generateQuestions } from './dpUtils.js';

const INITIAL_M = 3;
const INITIAL_N = 7;

function formatTime() {
  const now = new Date();
  return now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function App() {
  const m = INITIAL_M;
  const n = INITIAL_N;
  const answer = combinationPaths(m, n);

  const { steps, dp } = React.useMemo(() => generateSteps(m, n), [m, n]);
  const totalSteps = steps.length;

  const [currentStep, setCurrentStep] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(false);
  const [speed, setSpeed] = useState(1000);
  const [logEntries, setLogEntries] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [hasInteracted, setHasInteracted] = useState(false);
  const autoTimerRef = useRef(null);

  const addLog = useCallback((message, type = 'info') => {
    setLogEntries(prev => [...prev, { time: formatTime(), message, type }]);
  }, []);

  // Mark interaction when user steps forward
  useEffect(() => {
    if (currentStep > 0) {
      setHasInteracted(true);
    }
  }, [currentStep]);

  // Generate questions when step changes
  useEffect(() => {
    const qs = generateQuestions(m, n, currentStep, steps);
    setQuestions(qs);
  }, [currentStep, m, n, steps]);

  // Auto-play logic
  useEffect(() => {
    if (isAutoPlaying && currentStep < totalSteps - 1) {
      autoTimerRef.current = setTimeout(() => {
        setCurrentStep(prev => {
          const next = prev + 1;
          if (next >= totalSteps - 1) {
            setIsAutoPlaying(false);
            addLog('🎬 自动演示结束。你现在可以手动回看每一步。');
          }
          return next;
        });
      }, speed);
    } else if (currentStep >= totalSteps - 1) {
      setIsAutoPlaying(false);
    }
    return () => {
      if (autoTimerRef.current) clearTimeout(autoTimerRef.current);
    };
  }, [isAutoPlaying, currentStep, totalSteps, speed, addLog]);

  const handlePrev = useCallback(() => {
    setCurrentStep(prev => {
      const next = Math.max(0, prev - 1);
      if (next !== prev) {
        addLog(`⬅️ 回退到步骤 ${next + 1}：dp[${steps[next].i}][${steps[next].j}]`);
      }
      return next;
    });
  }, [steps, addLog]);

  const handleNext = useCallback(() => {
    setCurrentStep(prev => {
      const next = Math.min(totalSteps - 1, prev + 1);
      if (next !== prev) {
        const s = steps[next];
        if (s.isEdge) {
          addLog(`📐 步骤 ${next + 1}：设置边界 dp[${s.i}][${s.j}] = 1（第一行或第一列，只有一条路径）`);
        } else {
          const deps = s.dependencies;
          const parts = deps.map(d => `dp[${d.i}][${d.j}]=${d.value}`).join('  +  ');
          addLog(`🧮 步骤 ${next + 1}：计算 dp[${s.i}][${s.j}] = ${parts} = ${s.value}`);
        }
        if (next === totalSteps - 1) {
          addLog(`🎉 完成！最终答案 dp[${m - 1}][${n - 1}] = ${s.value}。组合数 C(${m + n - 2}, ${m - 1}) = ${s.value} ✓`, 'correct');
        }
      }
      return next;
    });
  }, [totalSteps, steps, addLog, m, n]);

  const handleReset = useCallback(() => {
    setCurrentStep(0);
    setIsAutoPlaying(false);
    addLog('🔄 重置 DP 表，从头开始探索。');
  }, [addLog]);

  const handleAutoPlay = useCallback(() => {
    if (currentStep >= totalSteps - 1) {
      // Reset and start
      setCurrentStep(0);
      setIsAutoPlaying(true);
      addLog('▶️ 从头开始自动演示...');
    } else {
      setIsAutoPlaying(prev => {
        const newState = !prev;
        addLog(newState ? '▶️ 开始自动演示...' : '⏸ 暂停自动演示。');
        return newState;
      });
    }
  }, [currentStep, totalSteps, addLog]);

  const handleSpeedChange = useCallback((ms) => {
    setSpeed(ms);
    const label = ms === 500 ? '快速' : ms === 1000 ? '正常' : '慢速';
    addLog(`⚡ 演示速度调整为 ${label}（${ms}ms/步）。`);
  }, [addLog]);

  const handleAnswer = useCallback((isCorrect, userInput) => {
    if (isCorrect) {
      addLog(`✅ 思考题回答正确！很棒！`, 'correct');
    } else {
      addLog(`❌ 思考题回答错误：输入了 "${userInput}"。查看提示再试试吧。`, 'incorrect');
    }
  }, [addLog]);

  const current = steps[Math.min(currentStep, steps.length - 1)];
  
  let formulaText = '';
  if (current && !current.isEdge && current.dependencies.length === 2) {
    formulaText = `dp[${current.i}][${current.j}] = dp[${current.i - 1}][${current.j}] + dp[${current.i}][${current.j - 1}] = ${current.dependencies[0].value} + ${current.dependencies[1].value} = ${current.value}`;
  } else if (current && current.isEdge) {
    formulaText = `dp[${current.i}][${current.j}] = 1 （边界：第一行或第一列，从起点出发只有一条路径可达）`;
  }

  return (
    <div className="container">
      <div className="header">
        <div className="header-left">
          <h1>不同路径</h1>
          <span className="badge">二维 DP</span>
        </div>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          交互式算法教学 · 逐步可视化
        </span>
      </div>

      <ProblemDisplay m={m} n={n} answer={answer} />

      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>📊 DP 表格可视化</h2>
          {current && (
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              当前：<strong>dp[{current.i}][{current.j}]</strong>
              <span className="badge" style={{ marginLeft: 8, fontSize: '0.7rem' }}>
                {current.isEdge ? '边界值' : '递推计算'}
              </span>
            </span>
          )}
        </div>

        {/* Prompt banner for first-time visitors */}
        {!hasInteracted && currentStep === 0 && (
          <div className="prompt-banner">
            <span style={{ fontSize: '1.3rem' }}>👆</span>
            <span>
              点击下方 <strong>"下一步 ▶"</strong> 按钮，或点击 <strong>"▶ 自动演示"</strong> 来逐步查看 DP 表格的填充过程。
              蓝色高亮格为当前正在计算的格子。
            </span>
          </div>
        )}

        {/* Controls placed above the grid for prominence */}
        <Controls
          currentStep={currentStep}
          totalSteps={totalSteps}
          onPrev={handlePrev}
          onNext={handleNext}
          onReset={handleReset}
          onAutoPlay={handleAutoPlay}
          isAutoPlaying={isAutoPlaying}
          speed={speed}
          onSpeedChange={handleSpeedChange}
        />

        <div style={{ marginTop: 20 }}>
          <DPTable m={m} n={n} steps={steps} currentStep={currentStep} dp={dp} />
        </div>

        {formulaText && (
          <div className="formula-box">
            <strong>📝 状态转移方程：</strong><br />
            <span className="math">{formulaText}</span>
          </div>
        )}

        <div className="legend">
          <div className="legend-item">
            <div className="legend-dot" style={{ background: 'var(--primary)', borderColor: 'var(--primary-dark)' }} />
            当前计算格（蓝）
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: '#fef3c7', borderColor: '#f59e0b' }} />
            依赖来源格（黄）
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: '#dbeafe', borderColor: '#93c5fd' }} />
            已计算（浅蓝）
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: '#dcfce7', borderColor: '#86efac' }} />
            边界值 = 1（绿）
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: '#f1f5f9', borderColor: 'var(--border)' }} />
            未计算（灰）
          </div>
        </div>
      </div>

      {/* Learning Objectives */}
      <div className="card" style={{ background: '#fffbeb', borderColor: '#fde68a' }}>
        <h3 style={{ marginBottom: 8 }}>🎯 学习目标</h3>
        <ul style={{ fontSize: '0.85rem', color: '#92400e', paddingLeft: 20, lineHeight: 1.9 }}>
          <li>认识二维 DP 表中 <code style={{ background: '#fef3c7', padding: '1px 5px', borderRadius: 3 }}>dp[i][j]</code> 表示从起点到 (i, j) 的路径数这一状态定义。</li>
          <li>能够根据当前格子的 i 和 j，预测 <code style={{ background: '#fef3c7', padding: '1px 5px', borderRadius: 3 }}>dp[i][j]</code> 依赖的 <code style={{ background: '#fef3c7', padding: '1px 5px', borderRadius: 3 }}>dp[i−1][j]</code> 与 <code style={{ background: '#fef3c7', padding: '1px 5px', borderRadius: 3 }}>dp[i][j−1]</code> 如何叠加。</li>
          <li>掌握如何利用组合数公式 <span className="math-display">C(m+n−2, m−1)</span> 验证 DP 结果，并理解状态转移与移动规则的对应关系。</li>
        </ul>
      </div>

      {/* Learner Checkpoints */}
      {questions.length > 0 && (
        <div>
          <h3 style={{ marginBottom: 12, marginTop: 4 }}>💭 思考与检验</h3>
          {questions.map((q, idx) => (
            <Checkpoint
              key={`${q.id}-${currentStep}`}
              question={q}
              questionIndex={idx}
              onAnswer={handleAnswer}
            />
          ))}
        </div>
      )}

      {/* Activity Log */}
      <ActivityLog entries={logEntries} />
    </div>
  );
}