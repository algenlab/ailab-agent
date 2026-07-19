
import React from 'react';

export default function StepNavigation({
  stepIndex,
  totalSteps,
  onPrev,
  onNext,
  onReset,
  canGoNext,
  currentStepDesc,
}) {
  const isLastStep = stepIndex === totalSteps - 1;

  return (
    <div className="step-nav">
      <div className="step-indicator">
        步骤 {stepIndex + 1} / {totalSteps}
        {isLastStep && ' (终)'}
      </div>
      <p className="step-description">{currentStepDesc}</p>
      <div className="step-buttons">
        <button onClick={onPrev} disabled={stepIndex === 0}>
          ← 上一步
        </button>
        <button onClick={onNext} disabled={!canGoNext}>
          {isLastStep ? '完成' : '下一步 →'}
        </button>
        <button onClick={onReset} className="reset-btn">
          🔄 重置
        </button>
      </div>
    </div>
  );
}
  