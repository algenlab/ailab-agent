import React from 'react';

export default function StepNavigator({
  currentStep,
  totalSteps,
  onStepChange,
  onShowHint,
  onShowAnswer,
  onReset,
  showAnswer,
  showHint,
}) {
  const progressPct = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0;

  return (
    <div className="card">
      <div className="card-header">⏯ 步骤导航</div>
      <div className="nav-bar">
        <button
          className="nav-btn"
          onClick={() => onStepChange(0)}
          disabled={currentStep === 0}
        >
          ⏮ 第一步
        </button>
        <button
          className="nav-btn"
          onClick={() => onStepChange(currentStep - 1)}
          disabled={currentStep === 0}
        >
          ◀ 上一步
        </button>
        <span className="step-indicator">
          步骤 {currentStep} / {totalSteps}
        </span>
        <button
          className="nav-btn"
          onClick={() => onStepChange(currentStep + 1)}
          disabled={currentStep === totalSteps || showAnswer}
        >
          下一步 ▶
        </button>
        <button
          className="nav-btn"
          onClick={() => onStepChange(totalSteps)}
          disabled={currentStep === totalSteps || showAnswer}
        >
          ⏭ 最后
        </button>
      </div>
      <div style={{ marginTop: '10px' }}>
        <div className="step-progress">
          <div
            className="step-progress-fill"
            style={{ width: `${Math.min(100, progressPct)}%` }}
          />
        </div>
      </div>
      <div className="nav-bar" style={{ marginTop: '12px' }}>
        <button
          className={`nav-btn hint-btn ${showHint ? 'hint-active' : ''}`}
          onClick={onShowHint}
        >
          💡 提示
        </button>
        <button
          className="nav-btn warn"
          onClick={onShowAnswer}
          disabled={showAnswer}
        >
          🔍 显示答案
        </button>
        <button className="nav-btn" onClick={onReset}>
          🔄 重置
        </button>
      </div>
    </div>
  );
}
