import React, { useState } from 'react';

export default function CheckpointPanel({ step, checkpointState, onCheckAnswer, onReset }) {
  const { active, question, userAnswer, feedback, locked } = checkpointState;
  const [input, setInput] = useState('');

  if (!active) {
    return (
      <div className="checkpoint-placeholder">
        <p><strong>No checkpoint at this step.</strong></p>
        <p>Navigate to <strong>Step 2</strong> (step index 1, where dp[0] and dp[1] have been computed) to predict the next DP value.</p>
      </div>
    );
  }

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    onCheckAnswer(input);
  };

  return (
    <div className="checkpoint-panel">
      <h3>Learn by Predicting: Checkpoint</h3>
      <p className="question">{question}</p>
      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={locked}
            placeholder="Your answer (number)"
            aria-label="Your prediction for the next dp value"
            autoComplete="off"
          />
          <button type="submit" disabled={locked || !input.trim()} className="check-btn">
            Check
          </button>
          {!locked && (
            <button type="button" onClick={onReset} className="reset-btn" aria-label="Reset checkpoint">
              ↺ Try Again
            </button>
          )}
        </div>
      </form>
      {feedback && (
        <div className={`feedback ${feedback.type}`} role="alert">
          {feedback.type === 'correct' ? '✅ ' : '❌ '}
          {feedback.message}
        </div>
      )}
      <style>{`
        .checkpoint-panel {
          background: #fef9c3;
          border: 2px solid #facc15;
          border-radius: 12px;
          padding: 20px;
          margin: 16px 0;
        }
        .checkpoint-placeholder {
          background: #f8fafc;
          border: 2px dashed #cbd5e1;
          border-radius: 12px;
          padding: 20px;
          margin: 16px 0;
          color: #475569;
        }
        .checkpoint-placeholder p {
          margin: 4px 0;
        }
        .checkpoint-panel h3 {
          margin-bottom: 8px;
          font-size: 1.1rem;
        }
        .question {
          margin-bottom: 12px;
          font-weight: 500;
          line-height: 1.5;
        }
        .input-group {
          display: flex;
          gap: 8px;
          align-items: center;
          flex-wrap: wrap;
        }
        .input-group input {
          padding: 8px 12px;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          font-size: 1rem;
          width: 150px;
          font-family: monospace;
          outline: none;
          transition: border-color 0.2s;
        }
        .input-group input:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
        }
        .check-btn, .reset-btn {
          padding: 8px 16px;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.2s;
          font-size: 0.9rem;
        }
        .check-btn {
          background: #2563eb;
          color: white;
        }
        .check-btn:disabled {
          background: #94a3b8;
          cursor: not-allowed;
        }
        .check-btn:hover:not(:disabled) {
          background: #1d4ed8;
        }
        .reset-btn {
          background: #e2e8f0;
          color: #1e293b;
        }
        .reset-btn:hover {
          background: #cbd5e1;
        }
        .feedback {
          margin-top: 12px;
          padding: 10px 14px;
          border-radius: 8px;
          font-weight: 500;
        }
        .feedback.correct {
          background: #dcfce7;
          color: #166534;
          border: 1px solid #bbf7d0;
        }
        .feedback.incorrect {
          background: #fee2e2;
          color: #991b1b;
          border: 1px solid #fecaca;
        }
      `}</style>
    </div>
  );
}