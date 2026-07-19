import React from 'react';
import './ProblemStatement.css';

export default function ProblemStatement({ base, exponent, mod, expected, answer, revealed, onReveal }) {
  return (
    <section className="problem-statement" aria-label="Problem Statement">
      <h2 className="section-title">Problem</h2>
      <p className="problem-description">
        In a security verification scenario, compute <strong>base<sup>exponent</sup> mod modulus</strong> using the fast power algorithm.
      </p>
      <div className="input-display">
        <div className="param">
          <span className="param-label">base</span>
          <span className="param-value">{base}</span>
        </div>
        <div className="param">
          <span className="param-label">exponent</span>
          <span className="param-value">{exponent}</span>
        </div>
        <div className="param">
          <span className="param-label">mod</span>
          <span className="param-value">{mod}</span>
        </div>
      </div>
      <div className="expected-answer">
        <div className="expected-text">
          <span className="expected-label">Expected Answer: </span>
          <span className="expected-value">
            {revealed ? <strong>{answer}</strong> : <em>?</em>}
          </span>
        </div>
        {!revealed && (
          <button className="reveal-btn" onClick={onReveal} aria-label="Reveal answer">
            👁 Reveal
          </button>
        )}
        {revealed && (
          <span className="revealed-badge">✓ Revealed</span>
        )}
      </div>
    </section>
  );
}
