import React, { useCallback, useRef } from 'react';

const PHASE_LABELS = {
  'initial': 'Introduction',
  'sort': 'Sorting',
  'lower': 'Lower Hull',
  'lower-done': 'Lower Done',
  'upper': 'Upper Hull',
  'upper-done': 'Upper Done',
  'combine': 'Combining',
  'done': 'Complete',
};

export default function StepControls({
  currentStep,
  totalSteps,
  onPrev,
  onNext,
  onGoTo,
  autoPlay,
  onToggleAutoPlay,
  phase,
}) {
  const progressRef = useRef(null);
  const progressPct = ((currentStep / (totalSteps - 1)) * 100).toFixed(0);
  const phaseLabel = PHASE_LABELS[phase] || phase;

  const handleProgressClick = useCallback(
    (e) => {
      if (!progressRef.current) return;
      const rect = progressRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const fraction = Math.max(0, Math.min(1, x / rect.width));
      const targetStep = Math.round(fraction * (totalSteps - 1));
      onGoTo(targetStep);
    },
    [onGoTo, totalSteps]
  );

  return (
    <div className="card step-controls">
      <button
        className="step-btn"
        onClick={onPrev}
        disabled={currentStep === 0}
        aria-label="Go to previous step"
      >
        ◀ Prev
      </button>
      <button
        className="step-btn primary-btn"
        onClick={onNext}
        disabled={currentStep >= totalSteps - 1}
        aria-label="Go to next step"
      >
        Next ▶
      </button>
      <button
        className={`step-btn ${autoPlay ? 'active' : ''}`}
        onClick={onToggleAutoPlay}
        aria-label={autoPlay ? 'Pause auto-play' : 'Start auto-play'}
        title={autoPlay ? 'Pause auto-play' : 'Auto-play through all steps'}
      >
        {autoPlay ? '\u23F8 Pause' : '\u25B6 Play'}
      </button>
      <div className="step-progress-wrap">
        <div
          className="step-progress"
          ref={progressRef}
          onClick={handleProgressClick}
          role="slider"
          aria-valuenow={currentStep}
          aria-valuemin={0}
          aria-valuemax={totalSteps - 1}
          aria-label="Step progress. Click to jump to a step."
          title="Click anywhere on the bar to jump to that step"
        >
          <div className="step-progress-fill" style={{ width: `${progressPct}%` }} />
        </div>
        <span className={`progress-phase-tag phase-${phase}`}>{phaseLabel}</span>
      </div>
      <span className="step-indicator">{currentStep}/{totalSteps - 1}</span>
    </div>
  );
}