import React, { useMemo } from 'react';
import IntervalBar from './IntervalBar';

export default function Visualization({
  stepData,
  currentStep,
  totalSteps,
  onNext,
  onPrev,
  onReset,
  onJumpToEnd,
  sortedIntervals,
  expectedOutput,
}) {
  const isFirst = currentStep === 0;
  const isLast = currentStep === totalSteps - 1;

  const displayedMerged = stepData.merged.length > 0 ? stepData.merged : null;
  const displayedCurrent = stepData.currentInterval;
  const actionText = stepData.action;

  // Compute all unique values for interval bar scale
  const allValues = useMemo(() => {
    const vals = [];
    sortedIntervals.forEach(([a, b]) => {
      vals.push(a);
      vals.push(b);
    });
    expectedOutput.forEach(([a, b]) => {
      vals.push(a);
      vals.push(b);
    });
    if (vals.length === 0) return [0, 20];
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const pad = Math.max(1, Math.ceil((max - min) * 0.1));
    return [Math.max(0, min - pad), max + pad];
  }, [sortedIntervals, expectedOutput]);

  const range = allValues[1] - allValues[0];

  function toPercent(v) {
    return ((v - allValues[0]) / range) * 100;
  }

  const futureIntervals = sortedIntervals.slice(stepData.index + 1);

  return (
    <div className="card">
      <div className="card-header">
        <span className="icon">📊</span>
        <h2>算法可视化</h2>
      </div>

      <div className="step-indicator">
        <span className="step-badge">
          步骤 {currentStep + 1} / {totalSteps}
        </span>
        <span className="step-desc">{actionText}</span>
      </div>

      {/* Interval Bar */}
      <IntervalBar
        allValues={allValues}
        range={range}
        toPercent={toPercent}
        merged={displayedMerged}
        current={displayedCurrent}
        future={futureIntervals}
        stepIndex={stepData.index}
      />

      {/* Merged State */}
      <div className="merged-display">
        <span className="label">📦 merged 列表</span>
        <div className="value">
          {displayedMerged ? JSON.stringify(displayedMerged) : '[]'}
        </div>
      </div>

      {/* Current interval being processed */}
      {displayedCurrent && (
        <div className="current-interval">
          <span className="tag">🔍 正在处理</span>
          <span className="val">[{displayedCurrent[0]}, {displayedCurrent[1]}]</span>
        </div>
      )}
      {!displayedCurrent && (
        <div className="current-interval">
          <span className="tag">🔍 正在处理</span>
          <span className="val">—</span>
        </div>
      )}

      {/* Sorted intervals reference */}
      <div style={{ marginTop: 8, fontSize: '0.78rem', color: '#94a3b8' }}>
        已排序区间：{JSON.stringify(sortedIntervals)}
        {stepData.index >= 0 && (
          <span>
            {' '}
            | 已处理：{stepData.index + 1}/{sortedIntervals.length}
          </span>
        )}
      </div>

      {/* Navigation Controls */}
      <div className="divider" />
      <div className="nav-controls">
        <button className="btn" onClick={onReset} disabled={isFirst}>
          🔄 重置
        </button>
        <button className="btn" onClick={onPrev} disabled={isFirst}>
          ◀ 上一步
        </button>
        <button className="btn btn-primary" onClick={onNext} disabled={isLast}>
          下一步 ▶
        </button>
        <button className="btn btn-warn" onClick={onJumpToEnd} disabled={isLast}>
          ⏩ 跳至结果
        </button>
      </div>

      {/* Auto-play hint */}
      <div style={{ marginTop: 8, fontSize: '0.75rem', color: '#94a3b8' }}>
        使用导航按钮逐步观察算法状态变化
      </div>
    </div>
  );
}
