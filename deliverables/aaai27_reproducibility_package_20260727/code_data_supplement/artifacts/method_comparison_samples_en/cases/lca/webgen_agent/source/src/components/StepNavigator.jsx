import React from 'react';

/**
 * StepNavigator — displays the current algorithm step and provides navigation controls.
 *
 * Props:
 *   step          : current step object from ALGORITHM_STEPS
 *   stepIndex     : current step index (0-based)
 *   totalSteps    : total number of steps
 *   onPrev        : go to previous step
 *   onNext        : go to next step
 *   onReset       : go to first step
 *   isAutoPlaying : whether auto-play is active
 *   onToggleAuto  : toggle auto-play
 */
export default function StepNavigator({
  step,
  stepIndex,
  totalSteps,
  onPrev,
  onNext,
  onReset,
  isAutoPlaying,
  onToggleAuto,
}) {
  if (!step) return null;

  const phaseLabel = step.phase.replace('_', ' ');
  const isLastStep = stepIndex === totalSteps - 1;
  const isFirstStep = stepIndex === 0;
  const isLcaStep = step.phase === 'lca_found';

  return (
    <div className="step-navigator">
      {/* Step indicator */}
      <div className="step-indicator">
        <span className="step-badge">
          Step {stepIndex + 1} of {totalSteps}
        </span>
        <span className={`phase-badge ${step.phase}`}>{phaseLabel}</span>
      </div>

      {/* Description */}
      <div className={`step-description${isLcaStep ? ' lca-highlight' : ''}`}>
        {step.description}
      </div>

      {/* Call stack */}
      <div>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-slate-500)', marginBottom: '0.25rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Call Stack
        </div>
        <div className="call-stack-display" aria-label={`Call stack: ${step.callStack.length ? step.callStack.join(', ') : 'empty'}`}>
          {step.callStack.length === 0 ? (
            <div className="call-stack-empty">— empty —</div>
          ) : (
            step.callStack.map((frame, i) => (
              <div key={i} className="call-stack-frame">{frame}</div>
            ))
          )}
        </div>
      </div>

      {/* Return value info */}
      <div className="return-info">
        <span>
          Left result:{' '}
          <span className={step.leftResult ? 'non-null' : 'null-val'}>
            {step.leftResult !== null ? `"${step.leftResult}"` : 'null'}
          </span>
        </span>
        <span>
          Right result:{' '}
          <span className={step.rightResult ? 'non-null' : 'null-val'}>
            {step.rightResult !== null ? `"${step.rightResult}"` : 'null'}
          </span>
        </span>
        <span>
          Return:{' '}
          <span className={step.returnValue ? 'non-null' : 'null-val'}>
            {step.returnValue !== null ? `"${step.returnValue}"` : '—'}
          </span>
        </span>
      </div>

      {/* Navigation controls */}
      <div className="nav-controls">
        <button
          className="btn btn-secondary"
          onClick={onPrev}
          disabled={isFirstStep}
          aria-label="Go to previous step"
        >
          ◀ Prev
        </button>
        <button
          className="btn btn-primary"
          onClick={onNext}
          disabled={isLastStep}
          aria-label="Go to next step"
        >
          Next ▶
        </button>
        <button
          className="btn btn-secondary"
          onClick={onReset}
          aria-label="Reset to first step"
        >
          ↺ Reset
        </button>
        <button
          className={`btn btn-auto${isAutoPlaying ? ' active' : ''}`}
          onClick={onToggleAuto}
          aria-label={isAutoPlaying ? 'Stop auto-play' : 'Start auto-play'}
        >
          {isAutoPlaying ? '⏸ Stop' : '▶ Auto'}
        </button>
      </div>
    </div>
  );
}
