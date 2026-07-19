import React from 'react';

export default function InputDisplay({ input, finalAnswer }) {
  return (
    <div className="input-display card">
      <h2>Problem Input</h2>
      <div className="input-row">
        <span className="label">k =</span>
        <code>{input.k}</code>
      </div>
      <div className="input-row">
        <span className="label">nums =</span>
        <code className="array-display">{JSON.stringify(input.nums)}</code>
      </div>
      <div className="final-answer">
        <span className="label">Expected Final Answer:</span>
        <code className="answer-value">{finalAnswer !== null ? finalAnswer : '—'}</code>
      </div>
    </div>
  );
}
  