import React from 'react';

export default function StepControls({ currentStep, totalSteps, onPrev, onNext, onReset, stepIndex }) {
  return (
    <div className="step-controls card">
      <div className="step-counter">
        Step {currentStep} / {totalSteps}
      </div>
      <div className="button-group">
        <button onClick={onReset} disabled={currentStep === 1} className="btn">
          ⟳ Reset
        </button>
        <button onClick={onPrev} disabled={currentStep <= 1} className="btn">
          ← Prev
        </button>
        <button onClick={onNext} disabled={currentStep >= totalSteps} className="btn">
          Next →
        </button>
      </div>
      <div className="current-num">
        {stepIndex > 0 && (
          <>
            Processing: <code className="num-highlight">{stepIndex}</code>
          </>
        )}
      </div>
    </div>
  );
}
  