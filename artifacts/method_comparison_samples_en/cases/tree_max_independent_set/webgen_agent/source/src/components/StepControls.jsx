import React from 'react';

export default function StepControls({
  currentStep,
  totalSteps,
  onPrev,
  onNext,
  onReset,
  autoPlay,
  onToggleAutoPlay
}) {
  return (
    <div className="step-controls">
      <button onClick={onPrev} disabled={currentStep <= 0} aria-label="Previous step">
        ◀ Prev
      </button>
      <span className="step-indicator">
        Step {currentStep + 1} / {totalSteps}
      </span>
      <button onClick={onNext} disabled={currentStep >= totalSteps - 1} aria-label="Next step">
        Next ▶
      </button>
      <button onClick={onReset} aria-label="Reset to beginning">
        ↺ Reset
      </button>
      <button
        onClick={onToggleAutoPlay}
        aria-label={autoPlay ? 'Stop auto-play' : 'Start auto-play'}
        style={{ marginLeft: 'auto' }}
      >
        {autoPlay ? '⏸ Stop' : '▶ Auto-play'}
      </button>
    </div>
  );
}