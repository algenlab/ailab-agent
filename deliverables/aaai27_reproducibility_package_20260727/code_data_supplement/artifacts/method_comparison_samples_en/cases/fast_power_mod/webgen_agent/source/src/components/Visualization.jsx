import React, { useState } from 'react';
import './Visualization.css';

const HINT_TEXT = `The fast power algorithm breaks the exponent into its binary representation. For each bit (from LSB to MSB):
1) If the bit is 1, multiply the current answer by cur, then take mod.
2) Square cur for the next bit: cur = (cur × cur) % mod.
3) Shift the exponent right (e >>= 1) to advance to the next bit.
This reduces multiplications from O(exponent) to O(log exponent).`;

export default function Visualization({
  steps,
  currentStep,
  onNext,
  onPrev,
  onReset,
  autoPlay,
  onToggleAuto,
  onStep,
  onShowAnswer,
  onHint,
  revealed
}) {
  const [hintVisible, setHintVisible] = useState(false);
  const step = steps[currentStep];
  if (!step) return null;

  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;
  const totalSteps = steps.length;

  const handleHintClick = () => {
    setHintVisible(prev => !prev);
    if (!hintVisible) {
      onHint();
    }
  };

  return (
    <section className="visualization" aria-label="Algorithm Visualization">
      <div className="viz-header">
        <h2 className="section-title">Step-by-Step Visualization</h2>
        <span className="step-counter">
          Step {currentStep + 1} of {totalSteps}
        </span>
      </div>

      {/* Primary navigation - prominently placed at the top */}
      <div className="viz-primary-nav">
        <button
          onClick={onPrev}
          disabled={isFirstStep}
          className="nav-btn"
          aria-label="Previous step"
        >
          ◀ Previous
        </button>
        <div className="viz-progress">
          {steps.map((_, idx) => (
            <div
              key={idx}
              className={`progress-dot ${idx === currentStep ? 'active' : ''} ${idx < currentStep ? 'past' : ''}`}
              onClick={() => onStep(idx)}
              title={`Go to step ${idx + 1}`}
            />
          ))}
        </div>
        <button
          onClick={onNext}
          disabled={isLastStep}
          className="nav-btn next-btn"
          aria-label="Next step"
        >
          Next ▶
        </button>
      </div>

      <div className="viz-grid">
        <div className="viz-card binary-card">
          <div className="viz-card-title">Exponent (binary)</div>
          <div className="binary-digits-wrapper">
            <BinaryDisplay exponent={steps[0]?.e ?? 0} currentBitPos={step.bitPos} currentStep={currentStep} />
          </div>
          <div className="viz-note">
            {step.bit !== null ? (
              <>Bit = <strong className="bit-highlight bit-val-1">{step.bit}</strong></>
            ) : (
              'Initial'
            )}
          </div>
        </div>

        <div className="viz-card">
          <div className="viz-card-title">Answer</div>
          <div className="viz-big-value">{step.answer}</div>
        </div>

        <div className="viz-card">
          <div className="viz-card-title">Cur (base<sup>2<sup>k</sup></sup>%mod)</div>
          <div className="viz-big-value">{step.cur}</div>
        </div>

        <div className="viz-card">
          <div className="viz-card-title">Remaining e</div>
          <div className="viz-big-value">{step.e}</div>
        </div>
      </div>

      <div className="powers-table-container">
        <h3 className="table-title">Powers Table</h3>
        <div className="table-scroll">
          <table className="powers-table">
            <thead>
              <tr>
                <th>k</th>
                <th>Bit</th>
                <th>cur (base<sup>2<sup>k</sup></sup>%mod)</th>
                <th>Multiply?</th>
              </tr>
            </thead>
            <tbody>
              <PowersTableRows steps={steps} currentStep={currentStep} />
            </tbody>
          </table>
        </div>
      </div>

      <div className="step-description">
        <span className="desc-icon">📝</span>
        <span>{step.description}</span>
      </div>

      {hintVisible && (
        <div className="viz-hint-box" role="alert">
          <strong>How It Works:</strong>
          <p>{HINT_TEXT}</p>
        </div>
      )}

      <div className="viz-controls">
        <div className="control-group">
          <button onClick={onReset} className="reset-btn" aria-label="Reset visualization">
            ⟳ Reset
          </button>
          <button
            onClick={onToggleAuto}
            className={`auto-btn ${autoPlay ? 'auto-active' : ''}`}
            aria-label={autoPlay ? 'Stop auto-play' : 'Start auto-play'}
          >
            {autoPlay ? '⏸ Stop Auto' : '▶ Auto Play'}
          </button>
        </div>
        <div className="control-group">
          <button
            className={`hint-btn ${hintVisible ? 'hint-active' : ''}`}
            onClick={handleHintClick}
            aria-label="Toggle algorithm hint"
          >
            💡 {hintVisible ? 'Hide Hint' : 'Hint'}
          </button>
          <button
            className="answer-btn"
            onClick={onShowAnswer}
            disabled={revealed}
            aria-label="Show final answer"
          >
            👁 {revealed ? 'Answer Shown' : 'Show Answer'}
          </button>
        </div>
      </div>
    </section>
  );
}

function BinaryDisplay({ exponent, currentBitPos, currentStep }) {
  if (!exponent && exponent !== 0) return null;
  const binary = exponent.toString(2);
  const len = binary.length;
  return (
    <span className="binary-digits">
      {binary.split('').map((char, idx) => {
        const bitPos = len - 1 - idx;
        const isCurrent = currentBitPos !== undefined && currentBitPos === bitPos && currentStep > 0 && currentStep < 6; // step 1-4 are processing steps
        return (
          <span
            key={idx}
            className={`bit-digit ${isCurrent ? 'current-bit' : ''} ${char === '1' ? 'is-one' : 'is-zero'}`}
            title={`Bit position ${bitPos} (weight 2^${bitPos})`}
          >
            {char}
          </span>
        );
      })}
    </span>
  );
}

function PowersTableRows({ steps, currentStep }) {
  const rows = [];
  const originalExponent = steps[0]?.e ?? 0;
  const binary = originalExponent.toString(2);
  const numBits = binary.length;

  for (let k = 0; k < numBits; k++) {
    const stepForBit = steps[k + 1];
    const bitValue = binary[numBits - 1 - k] === '1' ? 1 : 0;
    const powerAtStep = stepForBit ? stepForBit.curBeforeSquare : (steps[0] && k === 0 ? steps[0].cur : null);
    const isHighlighted = (currentStep - 1 === k);

    rows.push(
      <tr key={k} className={isHighlighted ? 'row-highlighted' : ''}>
        <td className="col-k">{k}</td>
        <td className={bitValue === 1 ? 'bit-one' : 'bit-zero'}>{bitValue}</td>
        <td className="col-cur">{powerAtStep !== null && powerAtStep !== undefined ? powerAtStep : '—'}</td>
        <td>
          {bitValue === 1 ? (
            <span className="used-yes">Yes ✓</span>
          ) : (
            <span className="used-no">No</span>
          )}
        </td>
      </tr>
    );
  }
  return rows;
}
