import React from 'react';

export default function ProblemDisplay({ amount, coins, finalAnswer }) {
  return (
    <div className="problem-display">
      <div className="problem-card input-card">
        <h3 className="card-label">Problem Input</h3>
        <div className="input-row">
          <span className="input-key">Amount:</span>
          <span className="input-value highlight-amount">{amount}</span>
        </div>
        <div className="input-row">
          <span className="input-key">Coins:</span>
          <span className="input-value">
            {coins.map((c, i) => (
              <span key={i} className="coin-badge">{c}</span>
            ))}
          </span>
        </div>
      </div>
      <div className="problem-card answer-card">
        <h3 className="card-label">Final Answer</h3>
        <div className="answer-value">
          {finalAnswer === -1 ? (
            <span className="answer-impossible">-1 (Impossible)</span>
          ) : (
            <span className="answer-number">{finalAnswer} coin{finalAnswer !== 1 ? 's' : ''}</span>
          )}
        </div>
      </div>
    </div>
  );
}
