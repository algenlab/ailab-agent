import React from 'react';
import './AlgorithmVisualizer.css';

export default function AlgorithmVisualizer({ state, stepIndex, totalSteps, onForward, onBackward, allSteps }) {
  const { i, seen, need, found, result, completed, nums, target } = state;

  const seenEntries = Object.entries(seen);
  const isAtStart = stepIndex === -1;
  const isAtEnd = stepIndex >= totalSteps - 1;

  // Determine which index is being processed
  const processingIndex = i >= 0 && i < nums.length ? i : -1;

  return (
    <section className="visualizer" aria-label="Algorithm step-by-step visualization">
      <h2 className="vis-title">Algorithm Visualization</h2>

      {/* Array display */}
      <div className="vis-array-section">
        <h3 className="vis-subtitle">Array (nums)</h3>
        <div className="vis-array">
          {nums.map((val, idx) => {
            let cellClass = 'vis-cell';
            if (found && result && (idx === result[0] || idx === result[1])) {
              cellClass += ' vis-cell-found';
            } else if (idx === processingIndex && found) {
              cellClass += ' vis-cell-found';
            } else if (idx === processingIndex && !completed) {
              cellClass += ' vis-cell-current';
            } else if (idx < processingIndex && !found) {
              cellClass += ' vis-cell-visited';
            }
            return (
              <div key={idx} className={cellClass}>
                <span className="vis-cell-index">i={idx}</span>
                <span className="vis-cell-value">{val}</span>
              </div>
            );
          })}
        </div>
        {processingIndex >= 0 && processingIndex < nums.length && (
          <div className="vis-current-info">
            <span className="vis-badge">Scanning index {processingIndex}</span>
            <span className="vis-badge vis-badge-need">Complement needed: {target} - {nums[processingIndex]} = {need}</span>
          </div>
        )}
      </div>

      {/* Hash Table display */}
      <div className="vis-seen-section">
        <h3 className="vis-subtitle">Hash Table (seen)</h3>
        <div className="vis-seen-table">
          {seenEntries.length === 0 ? (
            <div className="vis-seen-empty">Empty — no values seen yet</div>
          ) : (
            seenEntries.map(([val, idx]) => (
              <div key={val} className="vis-seen-entry">
                <span className="vis-seen-key">{val}</span>
                <span className="vis-seen-arrow">→</span>
                <span className="vis-seen-value">index {idx}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Step description */}
      <div className="vis-description">
        {isAtStart && (
          <p className="vis-desc-text">
            <strong>Initial state.</strong> The algorithm will traverse the array from left to right,
            using a hash table to remember which values have been seen and at which indices.
          </p>
        )}
        {!isAtStart && found && result && (
          <p className="vis-desc-text vis-desc-success">
            <strong>Match found!</strong> At index {processingIndex}, the complement <code>{need}</code> was found
            in the hash table at index {result[0]}. Result: [{result[0]}, {result[1]}].
          </p>
        )}
        {!isAtStart && !found && completed && processingIndex >= nums.length && (
          <p className="vis-desc-text vis-desc-fail">
            <strong>No solution found.</strong> The algorithm scanned all {nums.length} elements without finding
            a pair that sums to {target}.
          </p>
        )}
        {!isAtStart && !found && !completed && (
          <p className="vis-desc-text">
            At index <strong>{processingIndex}</strong>, the complement needed is <code>{need}</code>.
            {need in seen
              ? ` It is present in the hash table!`
              : ` It is NOT in the hash table. Adding nums[${processingIndex}] = ${nums[processingIndex]} to seen.`
            }
          </p>
        )}
      </div>

      {/* Navigation controls */}
      <div className="vis-controls">
        <button
          className="btn btn-outline"
          onClick={onBackward}
          disabled={isAtStart}
          aria-label="Previous step"
        >
          ← Previous
        </button>
        <span className="vis-step-counter">
          {isAtStart ? 'Start' : `Step ${stepIndex + 1} / ${totalSteps}`}
        </span>
        <button
          className="btn btn-outline"
          onClick={onForward}
          disabled={isAtEnd}
          aria-label="Next step"
        >
          Next →
        </button>
      </div>

      {/* Step overview dots */}
      <div className="vis-dots">
        {Array.from({ length: totalSteps }, (_, idx) => (
          <span
            key={idx}
            className={`vis-dot ${idx === stepIndex ? 'vis-dot-active' : ''} ${idx < stepIndex ? 'vis-dot-past' : ''}`}
            title={`Step ${idx + 1}`}
          />
        ))}
      </div>
    </section>
  );
}