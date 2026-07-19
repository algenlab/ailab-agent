import React from 'react';

export default function NavigationControls({
  currentStep,
  totalSteps,
  isAutoPlaying,
  speed,
  onStepPrev,
  onStepNext,
  onReset,
  onToggleAutoPlay,
  onSpeedChange,
}) {
  const canGoPrev = currentStep > 0;
  const canGoNext = currentStep < totalSteps - 1;
  const isAtEnd = currentStep === totalSteps - 1;

  return (
    <div className="card area-nav">
      <div className="card-header">
        <div className="icon icon-amber">🎮</div>
        <h2>步骤导航</h2>
      </div>
      <div className="nav-controls">
        <button
          className="nav-btn"
          onClick={onReset}
          disabled={currentStep === 0}
          title="重置到第一步"
        >
          ⏮ 重置
        </button>
        <button
          className="nav-btn"
          onClick={onStepPrev}
          disabled={!canGoPrev}
          title="上一步"
        >
          ◀ 上一步
        </button>

        <span className="nav-step-indicator">
          {currentStep + 1} / {totalSteps}
        </span>

        <button
          className="nav-btn"
          onClick={onStepNext}
          disabled={!canGoNext}
          title="下一步"
        >
          下一步 ▶
        </button>
        <button
          className={`nav-btn ${isAutoPlaying ? 'success' : 'primary'}`}
          onClick={onToggleAutoPlay}
          disabled={isAtEnd && !isAutoPlaying}
          title={isAutoPlaying ? '暂停' : '自动播放'}
        >
          {isAutoPlaying ? '⏸ 暂停' : '▶ 自动'}
        </button>
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', marginTop: '10px' }}>
        <div className="nav-speed-group">
          {[400, 800, 1500].map((ms) => (
            <button
              key={ms}
              className={`nav-speed-btn${speed === ms ? ' active' : ''}`}
              onClick={() => onSpeedChange(ms)}
            >
              {ms === 400 ? '⚡ 快' : ms === 800 ? '🕐 中' : '🐢 慢'}
            </button>
          ))}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ marginTop: '12px', height: '4px', background: '#E2E8F0', borderRadius: '2px', overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            background: 'var(--color-primary)',
            borderRadius: '2px',
            transition: 'width 0.3s ease',
            width: `${((currentStep + 1) / totalSteps) * 100}%`,
          }}
        />
      </div>
    </div>
  );
}
