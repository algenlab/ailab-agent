import React from 'react';

export default function StepNavigation({
  currentStepIndex,
  totalSteps,
  currentStep,
  onPrev,
  onNext,
  onGoTo,
  autoPlay,
  onToggleAutoPlay
}) {
  const progressPct = totalSteps > 1 ? Math.round((currentStepIndex / (totalSteps - 1)) * 100) : 0;

  return (
    <div className="step-navigation">
      <div className="nav-controls">
        <button
          className="btn btn-nav"
          onClick={onPrev}
          disabled={currentStepIndex <= 0}
          aria-label="Previous step"
        >
          ◀ Prev
        </button>

        <div className="nav-step-indicator">
          <span className="step-count">
            Step {currentStepIndex + 1} of {totalSteps}
          </span>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progressPct}%` }}></div>
          </div>
        </div>

        <button
          className="btn btn-nav"
          onClick={onNext}
          disabled={currentStepIndex >= totalSteps - 1}
          aria-label="Next step"
        >
          Next ▶
        </button>

        <button
          className={`btn btn-autoplay ${autoPlay ? 'autoplay-active' : ''}`}
          onClick={onToggleAutoPlay}
          aria-label={autoPlay ? 'Pause auto-play' : 'Start auto-play'}
        >
          {autoPlay ? '⏸ Pause' : '▶ Auto'}
        </button>
      </div>

      <div className="nav-step-info">
        <div className="step-description">
          <span className={`step-badge step-badge-${currentStep.type}`}>
            {currentStep.type === 'init' ? 'Init' :
             currentStep.type === 'coin-start' ? `Coin ${currentStep.coin} Start` :
             `Update`}
          </span>
          <span className="step-desc-text">{currentStep.description}</span>
        </div>
      </div>

      <div className="nav-timeline">
        <input
          type="range"
          min={0}
          max={totalSteps - 1}
          value={currentStepIndex}
          onChange={(e) => onGoTo(parseInt(e.target.value, 10))}
          className="timeline-slider"
          aria-label="Step timeline slider"
        />
        <div className="timeline-labels">
          <span>Start</span>
          <span>End</span>
        </div>
      </div>
    </div>
  );
}
