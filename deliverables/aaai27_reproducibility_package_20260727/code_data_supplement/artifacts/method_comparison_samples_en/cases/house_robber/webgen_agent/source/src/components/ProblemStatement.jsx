import React from 'react';

export default function ProblemStatement({ inputArray, finalAnswer, revealAnswer, customInput, onCustomInputChange, onApplyCustomInput, onResetToDefault, isDefault }) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      onApplyCustomInput();
    }
  };

  return (
    <section className="problem-statement">
      <h2>Problem</h2>
      <p>
        A thief plans to rob houses along a straight line. Each house contains a certain amount of cash, represented by the array <code>nums</code>.
        Adjacent houses have connected alarms; robbing two adjacent houses triggers the alarm.
        Help the thief calculate the <strong>maximum total amount</strong> of money that can be robbed without triggering the alarm.
      </p>
      <div className="io-box">
        <div className="input-group-custom">
          <label htmlFor="custom-input" className="label">Input (nums):</label>
          <div className="input-row">
            <input
              id="custom-input"
              type="text"
              value={customInput}
              onChange={(e) => onCustomInputChange(e.target.value)}
              onKeyDown={handleKeyDown}
              className="value editable"
              aria-label="Custom input array as comma-separated integers"
              placeholder="e.g., 2, 7, 9, 3, 1"
            />
            <button onClick={onApplyCustomInput} className="apply-btn" aria-label="Apply custom input">
              Apply
            </button>
            {!isDefault && (
              <button onClick={onResetToDefault} className="reset-default-btn" aria-label="Reset to default input">
                Reset Default
              </button>
            )}
          </div>
        </div>
        <div className="output-group">
          <span className="label">Final Answer:</span>
          {revealAnswer ? (
            <span className="value answer">{finalAnswer}</span>
          ) : (
            <span className="value answer-hidden" title="Complete all steps to reveal the final answer">
              Complete all steps to reveal
            </span>
          )}
        </div>
      </div>
      <style>{`
        .problem-statement {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 20px 24px;
          margin-bottom: 24px;
        }
        .problem-statement h2 {
          font-size: 1.4rem;
          margin-bottom: 8px;
        }
        .problem-statement p {
          margin-bottom: 14px;
        }
        .io-box {
          display: flex;
          gap: 32px;
          flex-wrap: wrap;
          margin-top: 12px;
          align-items: center;
        }
        .input-group-custom {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .input-row {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }
        .output-group {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .io-box .label {
          font-weight: 600;
          font-size: 0.95rem;
          white-space: nowrap;
        }
        .io-box .value {
          font-family: monospace;
          font-size: 1rem;
          background: white;
          padding: 4px 12px;
          border-radius: 6px;
          border: 1px solid #cbd5e1;
        }
        .io-box .editable {
          width: 220px;
          outline: none;
          transition: border-color 0.2s;
        }
        .io-box .editable:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
        }
        .io-box .answer {
          color: #0f766e;
          font-weight: 700;
          background: #f0fdf4;
          border-color: #4ade80;
        }
        .io-box .answer-hidden {
          color: #94a3b8;
          font-style: italic;
          font-family: system-ui, -apple-system, sans-serif;
          font-size: 0.9rem;
          border-style: dashed;
        }
        .apply-btn {
          padding: 5px 14px;
          background: #2563eb;
          color: white;
          border: none;
          border-radius: 6px;
          font-weight: 600;
          cursor: pointer;
          font-size: 0.85rem;
          transition: background 0.2s;
        }
        .apply-btn:hover {
          background: #1d4ed8;
        }
        .reset-default-btn {
          padding: 5px 14px;
          background: #e2e8f0;
          color: #1e293b;
          border: none;
          border-radius: 6px;
          font-weight: 600;
          cursor: pointer;
          font-size: 0.85rem;
          transition: background 0.2s;
        }
        .reset-default-btn:hover {
          background: #cbd5e1;
        }
        @media (max-width: 640px) {
          .problem-statement {
            padding: 16px;
          }
          .io-box {
            flex-direction: column;
            align-items: flex-start;
            gap: 16px;
          }
          .input-row {
            flex-direction: column;
            align-items: flex-start;
          }
          .io-box .editable {
            width: 100%;
          }
        }
      `}</style>
    </section>
  );
}