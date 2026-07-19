import React from 'react';

export default function Controls({
  currentStep,
  totalSteps,
  onPrev,
  onNext,
  onReset,
  onAutoPlay,
  isAutoPlaying,
  speed,
  onSpeedChange
}) {
  const progressPercent = ((currentStep + 1) / totalSteps) * 100;
  const isComplete = currentStep >= totalSteps - 1;
  const isStart = currentStep === 0;

  return (
    <div>
      <div className="step-indicator">
        <span style={{ fontWeight: 700, fontSize: '1rem' }}>
          步骤 {currentStep + 1} / {totalSteps}
        </span>
        {isComplete && (
          <span className="badge badge-success">✓ 已完成全部计算</span>
        )}
        {isStart && !isComplete && (
          <span className="badge" style={{ background: '#fef3c7', color: '#92400e', borderColor: '#fde68a' }}>
            准备开始
          </span>
        )}
        {!isStart && !isComplete && (
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            进度 {Math.round(progressPercent)}%
          </span>
        )}
      </div>

      <div className="progress-bar">
        <div
          className="progress-bar-fill"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      <div className="btn-group" style={{ marginTop: 14 }}>
        <button
          className="btn btn-outline"
          onClick={onReset}
          disabled={isStart}
          title="回到第一步"
        >
          ⏮ 重置
        </button>
        <button
          className="btn btn-primary"
          onClick={onPrev}
          disabled={isStart}
          title="上一步"
        >
          ◀ 上一步
        </button>
        <button
          className="btn btn-primary btn-lg"
          onClick={onNext}
          disabled={isComplete}
          title="下一步"
          style={{ minWidth: 120 }}
        >
          下一步 ▶
        </button>
        <button
          className={isAutoPlaying ? 'btn btn-warning' : 'btn btn-success'}
          onClick={onAutoPlay}
          title={isAutoPlaying ? '暂停自动演示' : '自动逐步演示'}
        >
          {isAutoPlaying ? '⏸ 暂停' : '▶ 自动演示'}
        </button>
      </div>

      <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>速度：</span>
        {[
          { ms: 500, label: '快速' },
          { ms: 1000, label: '正常' },
          { ms: 2000, label: '慢速' }
        ].map(({ ms, label }) => (
          <button
            key={ms}
            className={`btn btn-sm ${speed === ms ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => onSpeedChange(ms)}
          >
            {label} {ms}ms
          </button>
        ))}
      </div>
    </div>
  );
}