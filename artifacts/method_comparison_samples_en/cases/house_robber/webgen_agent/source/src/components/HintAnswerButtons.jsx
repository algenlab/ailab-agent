import React from 'react';

export default function HintAnswerButtons({ onHint, onShowAnswer, hintVisible, answerVisible, answerValue }) {
  return (
    <div className="hint-answer-buttons">
      <button onClick={onHint} className="hint-btn" aria-label="Show hint">
        💡 Hint
      </button>
      <button onClick={onShowAnswer} className="reveal-btn" aria-label="Show answer">
        🔎 Show Answer
      </button>
      {hintVisible && (
        <div className="hint-box">
          <strong>Hint:</strong> Use the recurrence <code>dp[i] = max(dp[i-1], dp[i-2] + nums[i])</code> with i=2.
        </div>
      )}
      {answerVisible && (
        <div className="answer-box">
          <strong>Answer:</strong> The correct dp[2] is <span className="revealed-answer">{answerValue}</span>.
        </div>
      )}
      <style>{`
        .hint-answer-buttons {
          display: flex;
          gap: 10px;
          margin: 12px 0;
          flex-wrap: wrap;
        }
        .hint-btn, .reveal-btn {
          padding: 8px 16px;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
        }
        .hint-btn {
          background: #e0f2fe;
          color: #0369a1;
        }
        .reveal-btn {
          background: #ddd6fe;
          color: #5b21b6;
        }
        .hint-btn:hover, .reveal-btn:hover {
          filter: brightness(0.95);
        }
        .hint-box, .answer-box {
          width: 100%;
          background: #f0f9ff;
          border: 1px solid #bae6fd;
          border-radius: 8px;
          padding: 10px 14px;
          margin-top: 4px;
        }
        .answer-box {
          background: #f5f3ff;
          border-color: #ddd6fe;
        }
        .revealed-answer {
          font-weight: 700;
          font-family: monospace;
          font-size: 1.1rem;
        }
      `}</style>
    </div>
  );
}