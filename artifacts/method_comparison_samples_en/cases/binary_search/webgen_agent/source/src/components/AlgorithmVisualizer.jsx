import React, { useState, useCallback, useMemo } from 'react';

function computeSteps(nums, target) {
  const steps = [];
  let left = 0;
  let right = nums.length - 1;

  steps.push({
    left,
    right,
    mid: null,
    numsAtMid: null,
    comparison: null,
    action: 'Initial state: search interval [' + left + ', ' + right + ']',
  });

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const numsAtMid = nums[mid];

    if (numsAtMid === target) {
      steps.push({
        left,
        right,
        mid,
        numsAtMid,
        comparison: 'equal',
        action: 'nums[' + mid + '] = ' + numsAtMid + ' == ' + target + '. Target found at index ' + mid + '!',
      });
      return steps;
    } else if (numsAtMid < target) {
      steps.push({
        left,
        right,
        mid,
        numsAtMid,
        comparison: 'less',
        action: 'nums[' + mid + '] = ' + numsAtMid + ' < ' + target + '. Discard left half. Move left to ' + (mid + 1) + '.',
      });
      left = mid + 1;
    } else {
      steps.push({
        left,
        right,
        mid,
        numsAtMid,
        comparison: 'greater',
        action: 'nums[' + mid + '] = ' + numsAtMid + ' > ' + target + '. Discard right half. Move right to ' + (mid - 1) + '.',
      });
      right = mid - 1;
    }
  }

  steps.push({
    left,
    right,
    mid: null,
    numsAtMid: null,
    comparison: 'not_found',
    action: 'Search complete. Target not found. Return -1.',
  });

  return steps;
}

export default function AlgorithmVisualizer({ nums, target, finalAnswer, addLogEntry }) {
  const steps = useMemo(() => computeSteps(nums, target), [nums, target]);
  const [currentStep, setCurrentStep] = useState(0);

  const step = steps[currentStep] || steps[steps.length - 1];
  const totalSteps = steps.length;
  const isLastStep = currentStep >= steps.length - 1;
  const isFirstStep = currentStep <= 0;
  const isFound = step.comparison === 'equal';

  const goToStep = useCallback(
    (index) => {
      const clamped = Math.max(0, Math.min(index, steps.length - 1));
      setCurrentStep(clamped);
      if (clamped > 0) {
        addLogEntry('step', 'Navigated to step ' + (clamped) + ' of ' + (steps.length - 1));
      }
    },
    [steps.length, addLogEntry]
  );

  const handlePrev = useCallback(() => {
    if (!isFirstStep) {
      goToStep(currentStep - 1);
    }
  }, [currentStep, isFirstStep, goToStep]);

  const handleNext = useCallback(() => {
    if (!isLastStep) {
      goToStep(currentStep + 1);
    }
  }, [currentStep, isLastStep, goToStep]);

  const handleReset = useCallback(() => {
    goToStep(0);
    addLogEntry('step', 'Reset visualization to initial state');
  }, [goToStep, addLogEntry]);

  const handleAutoPlay = useCallback(() => {
    addLogEntry('step', 'Auto-playing all steps');
    setCurrentStep(0);
    let i = 0;
    const interval = setInterval(() => {
      i++;
      if (i >= steps.length) {
        clearInterval(interval);
      } else {
        setCurrentStep(i);
      }
    }, 800);
  }, [steps.length, addLogEntry]);

  const progressPercent =
    totalSteps > 1 ? Math.round(((currentStep) / (totalSteps - 1)) * 100) : 0;

  return (
    <section className="section">
      <h2 className="section-title">
        <span className="icon" role="img" aria-label="visualize">🔍</span>
        Step-by-Step Visualization
      </h2>

      {/* Array visualization */}
      <div className="array-vis">
        {nums.map((val, idx) => {
          let cellClass = 'array-cell';
          if (step.comparison === 'equal' && step.mid === idx) {
            cellClass += ' found';
          } else if (step.mid === idx && step.comparison !== 'not_found') {
            cellClass += ' mid-pointer';
          } else if (step.left === idx && step.right === idx && step.comparison !== 'equal') {
            // left and right same cell
          } else if (step.left === idx) {
            cellClass += ' left-pointer';
          } else if (step.right === idx) {
            cellClass += ' right-pointer';
          }

          // Discard styling: if comparison was 'less' and idx <= mid, or 'greater' and idx >= mid
          if (
            step.comparison === 'less' &&
            step.mid !== null &&
            idx <= step.mid &&
            idx !== step.mid
          ) {
            cellClass += ' discarded';
          }
          if (
            step.comparison === 'greater' &&
            step.mid !== null &&
            idx >= step.mid &&
            idx !== step.mid
          ) {
            cellClass += ' discarded';
          }
          if (step.left !== null && idx < step.left) {
            cellClass += ' discarded';
          }
          if (step.right !== null && idx > step.right) {
            cellClass += ' discarded';
          }

          return (
            <div key={idx} className={cellClass} title={'Index ' + idx + ': ' + val}>
              <span>{val}</span>
              <span className="cell-index">{idx}</span>
            </div>
          );
        })}
      </div>

      {/* Pointer legend */}
      <div className="pointer-legend">
        <span className="legend-item">
          <span className="legend-dot left"></span> Left pointer
        </span>
        <span className="legend-item">
          <span className="legend-dot mid"></span> Mid pointer
        </span>
        <span className="legend-item">
          <span className="legend-dot right"></span> Right pointer
        </span>
        <span className="legend-item">
          <span className="legend-dot discarded"></span> Discarded region
        </span>
      </div>

      {/* State cards */}
      <div className="state-info">
        <div className="state-card left-card">
          <div className="state-label">Left Index</div>
          <div className="state-value">{step.left !== null ? step.left : '—'}</div>
        </div>
        <div className="state-card mid-card">
          <div className="state-label">Mid Index</div>
          <div className="state-value">{step.mid !== null ? step.mid : '—'}</div>
        </div>
        <div className="state-card right-card">
          <div className="state-label">Right Index</div>
          <div className="state-value">{step.right !== null ? step.right : '—'}</div>
        </div>
        <div className="state-card mid-card">
          <div className="state-label">nums[mid]</div>
          <div className="state-value">{step.numsAtMid !== null ? step.numsAtMid : '—'}</div>
        </div>
        <div className="state-card">
          <div className="state-label">Comparison</div>
          <div className="state-value">
            {step.comparison === 'less'
              ? 'nums[mid] < target'
              : step.comparison === 'greater'
                ? 'nums[mid] > target'
                : step.comparison === 'equal'
                  ? 'nums[mid] == target ✓'
                  : '—'}
          </div>
        </div>
      </div>

      {/* Action description */}
      <div
        style={{
          marginTop: '14px',
          padding: '12px 16px',
          background: isFound ? '#dcfce7' : '#f8fafc',
          borderRadius: '8px',
          border: '1px solid ' + (isFound ? '#16a34a' : '#e2e8f0'),
          fontSize: '0.95rem',
          fontWeight: 500,
        }}
      >
        {step.action}
      </div>

      {/* Progress */}
      <div className="progress-bar" style={{ marginTop: '16px' }}>
        <div className="progress-fill" style={{ width: progressPercent + '%' }}></div>
      </div>

      {/* Controls */}
      <div className="controls">
        <span className="step-counter">
          Step {currentStep > 0 ? currentStep : 0} / {totalSteps - 1}
        </span>
        <button className="btn" onClick={handleReset} disabled={isFirstStep && currentStep === 0}>
          ⟲ Reset
        </button>
        <button className="btn" onClick={handlePrev} disabled={isFirstStep}>
          ← Previous
        </button>
        <button className="btn btn-primary" onClick={handleNext} disabled={isLastStep}>
          Next →
        </button>
        <button className="btn btn-warning" onClick={handleAutoPlay}>
          ▶ Auto Play
        </button>
        <div style={{ display: 'flex', gap: '6px', marginLeft: '8px' }}>
          {steps.slice(1).map((s, i) => {
            const stepNum = i + 1;
            const isCurrent = stepNum === currentStep;
            const isPast = stepNum < currentStep;
            let btnStyle = {};
            if (isCurrent) btnStyle = { background: '#2563eb', color: '#fff', borderColor: '#2563eb' };
            else if (isPast && s.comparison === 'equal') btnStyle = { background: '#dcfce7', borderColor: '#16a34a' };
            else if (isPast) btnStyle = { background: '#f1f5f9' };

            return (
              <button
                key={stepNum}
                className="btn btn-sm"
                style={btnStyle}
                onClick={() => goToStep(stepNum)}
                title={'Go to step ' + stepNum}
              >
                {stepNum}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
