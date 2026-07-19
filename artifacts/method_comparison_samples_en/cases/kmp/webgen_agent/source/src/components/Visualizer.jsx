import React from 'react';

export default function Visualizer({ pattern, text, step, stepIndex, totalSteps, onPrev, onNext }) {
  const { state, title, description } = step;

  const textChars = text.split('');
  const patternChars = pattern.split('');

  // Determine which indices to highlight
  let textHighlight = -1;
  let patternHighlight = -1;

  if (state.phase === 'match') {
    if (state.textIndex !== undefined && state.textIndex !== null) {
      textHighlight = state.textIndex;
    }
    if (state.patternIndex !== undefined && state.patternIndex !== null) {
      patternHighlight = state.patternIndex;
    }
  }

  return (
    <div className="visualizer">
      <div className="step-header">
        <span className="step-badge">Step {stepIndex + 1} of {totalSteps}</span>
        <span className={`step-type-badge ${step.type}`}>{step.type.replace(/_/g, ' ')}</span>
      </div>

      <h3 className="step-title">{title}</h3>
      <p className="step-description">{description}</p>

      {/* Text and Pattern Visualization */}
      <div className="viz-section">
        {/* Only show text/pattern comparison during matching phase */}
        {state.phase === 'match' && (
          <>
            <div className="viz-row">
              <span className="viz-label">Text:</span>
              <div className="char-array">
                {textChars.map((ch, idx) => (
                  <span
                    key={idx}
                    className={`char-box ${idx === textHighlight ? 'highlight current' : ''} ${state.matchStatus === 'match' && idx === textHighlight ? 'match-char' : ''} ${state.matchStatus === 'mismatch_backtrack' && idx === textHighlight ? 'mismatch-char' : ''}`}
                  >
                    {ch}
                  </span>
                ))}
              </div>
            </div>
            <div className="viz-indices">
              <span className="viz-label"></span>
              <div className="char-array indices">
                {textChars.map((_, idx) => (
                  <span key={idx} className={`index-box ${idx === textHighlight ? 'highlight-index' : ''}`}>
                    {idx}
                  </span>
                ))}
              </div>
            </div>

            {/* Arrow pointer for text */}
            <div className="viz-pointer">
              <span className="viz-label">i={state.i !== undefined ? state.i : '?'}</span>
              <div className="char-array pointer-row">
                {textChars.map((_, idx) => (
                  <span key={idx} className="index-box pointer">
                    {idx === textHighlight ? '▲' : ''}
                  </span>
                ))}
              </div>
            </div>

            <div className="viz-row" style={{ marginTop: '16px' }}>
              <span className="viz-label">Pattern:</span>
              <div className="char-array">
                {patternChars.map((ch, idx) => (
                  <span
                    key={idx}
                    className={`char-box ${idx === patternHighlight ? 'highlight current' : ''} ${state.matchStatus === 'match' && idx === patternHighlight ? 'match-char' : ''} ${state.matchStatus === 'mismatch_backtrack' && idx === patternHighlight ? 'mismatch-char' : ''}`}
                  >
                    {ch}
                  </span>
                ))}
              </div>
            </div>
            <div className="viz-indices">
              <span className="viz-label"></span>
              <div className="char-array indices">
                {patternChars.map((_, idx) => (
                  <span key={idx} className={`index-box ${idx === patternHighlight ? 'highlight-index' : ''}`}>
                    {idx}
                  </span>
                ))}
              </div>
            </div>
            <div className="viz-pointer">
              <span className="viz-label">j={state.j !== undefined ? state.j : '?'}</span>
              <div className="char-array pointer-row">
                {patternChars.map((_, idx) => (
                  <span key={idx} className="index-box pointer">
                    {idx === patternHighlight ? '▲' : ''}
                  </span>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Prefix table display */}
        {state.phase === 'prefix' && (
          <div className="prefix-viz">
            <h4>Building Prefix Table (pi)</h4>
            <div className="viz-row">
              <span className="viz-label">Pattern:</span>
              <div className="char-array">
                {patternChars.map((ch, idx) => (
                  <span
                    key={idx}
                    className={`char-box ${idx === state.i ? 'highlight current' : ''} ${idx === state.j ? 'highlight j-highlight' : ''}`}
                  >
                    {ch}
                  </span>
                ))}
              </div>
            </div>
            <div className="viz-row">
              <span className="viz-label">pi:</span>
              <div className="char-array pi-array">
                {(state.pi || []).map((val, idx) => (
                  <span key={idx} className="pi-box">
                    {val}
                  </span>
                ))}
                {state.pi && state.pi.length < pattern.length && (
                  <span className="pi-box pi-empty">?</span>
                )}
              </div>
            </div>
            <div className="viz-row" style={{ marginTop: '8px' }}>
              <span className="viz-label">i={state.i !== undefined ? state.i : '?'}</span>
              <span className="viz-label" style={{ marginLeft: '16px' }}>j={state.j !== undefined ? state.j : '?'}</span>
            </div>
          </div>
        )}

        {/* Show result if found */}
        {state.matchStatus === 'found' && (
          <div className="result-display">
            <span className="result-badge">Result: {state.result}</span>
          </div>
        )}
        {state.matchStatus === 'not_found' && (
          <div className="result-display">
            <span className="result-badge not-found">Result: -1</span>
          </div>
        )}
      </div>

      {/* Navigation Controls */}
      <div className="nav-controls">
        <button
          onClick={onPrev}
          disabled={stepIndex === 0}
          className="nav-btn"
          aria-label="Previous step"
        >
          ← Previous
        </button>
        <button
          onClick={onNext}
          disabled={stepIndex === totalSteps - 1}
          className="nav-btn"
          aria-label="Next step"
        >
          Next →
        </button>
      </div>
    </div>
  );
}