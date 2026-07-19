import React from 'react';
import './StepNavigator.css';

export default function StepNavigator({ steps, currentStep, onGoToStep, onNext, onPrev, isFirstStep, isLastStep }) {
  return (
    <div className="step-navigator">
      <div className="step-detail">
        <div className="step-description">
          <span className="step-number">{currentStep + 1} / {steps.length}</span>
          <p>{steps[currentStep]?.description}</p>
          {steps[currentStep]?.subInfo && (
            <p className="step-sub-info">{steps[currentStep]?.subInfo}</p>
          )}
        </div>
      </div>

      <div className="step-controls">
        <button
          className="btn btn-prev"
          onClick={onPrev}
          disabled={isFirstStep}
        >
          ← 上一步
        </button>

        <div className="step-dots">
          {steps.map((s, i) => (
            <button
              key={s.id}
              className={`step-dot ${i === currentStep ? 'step-dot--active' : ''} ${i < currentStep ? 'step-dot--done' : ''}`}
              onClick={() => onGoToStep(i)}
              title={s.title}
            >
              {i + 1}
            </button>
          ))}
        </div>

        <button
          className="btn btn-next"
          onClick={onNext}
          disabled={isLastStep}
        >
          下一步 →
        </button>
      </div>
    </div>
  );
}
