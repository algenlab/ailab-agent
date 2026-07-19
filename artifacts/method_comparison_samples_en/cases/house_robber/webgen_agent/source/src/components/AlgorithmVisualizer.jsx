import React from 'react';

export default function AlgorithmVisualizer({ step, currentStepIndex, totalSteps }) {
  const { nums, dp, houseIndex, explanation } = step;

  return (
    <div className="algorithm-visualizer">
      <div className="step-indicator">
        Step {currentStepIndex + 1} of {totalSteps} — processing house index <strong>{houseIndex}</strong>
      </div>
      <div className="dp-array">
        <div className="array-row">
          <span className="row-label">nums</span>
          {nums.map((val, idx) => (
            <div key={`nums-${idx}`} className={`cell nums-cell ${idx === houseIndex ? 'active' : ''} ${idx < houseIndex ? 'past' : ''}`}>
              <span className="index">i={idx}</span>
              <span className="value">{val}</span>
            </div>
          ))}
        </div>
        <div className="array-row">
          <span className="row-label">dp</span>
          {dp.map((val, idx) => {
            const filled = idx <= houseIndex;
            return (
              <div key={`dp-${idx}`} className={`cell dp-cell ${idx === houseIndex ? 'active' : ''} ${filled ? 'computed' : 'empty'}`}>
                <span className="index">i={idx}</span>
                <span className="value">{filled ? val : '?'}</span>
              </div>
            );
          })}
          {/* Placeholder for future dp cells */}
          {dp.length < nums.length &&
            Array.from({ length: nums.length - dp.length }).map((_, i) => {
              const idx = dp.length + i;
              return (
                <div key={`dp-empty-${idx}`} className="cell dp-cell empty">
                  <span className="index">i={idx}</span>
                  <span className="value">?</span>
                </div>
              );
            })
          }
        </div>
      </div>
      <div className="explanation">
        <p>{explanation}</p>
      </div>
      <style>{`
        .algorithm-visualizer {
          margin: 16px 0;
          overflow-x: auto;
        }
        .step-indicator {
          font-weight: 600;
          margin-bottom: 16px;
          font-size: 1rem;
          color: #334155;
          padding: 8px 12px;
          background: #e2e8f0;
          border-radius: 8px;
          display: inline-block;
        }
        .dp-array {
          margin: 12px 0;
          min-width: max-content;
        }
        .array-row {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 12px;
          flex-wrap: nowrap;
          min-width: fit-content;
        }
        .row-label {
          font-weight: 700;
          font-family: monospace;
          min-width: 52px;
          text-align: right;
          font-size: 1rem;
          color: #1e293b;
          flex-shrink: 0;
        }
        .cell {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          width: 64px;
          min-width: 64px;
          padding: 10px 6px;
          border-radius: 10px;
          border: 2px solid #e2e8f0;
          background: white;
          transition: all 0.25s ease;
          flex-shrink: 0;
        }
        .cell .index {
          font-size: 0.65rem;
          color: #64748b;
          margin-bottom: 3px;
          font-family: monospace;
          font-weight: 500;
        }
        .cell .value {
          font-size: 1.3rem;
          font-weight: 700;
          font-family: monospace;
          line-height: 1.2;
        }
        .nums-cell.active {
          border-color: #3b82f6;
          background: #dbeafe;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
        }
        .nums-cell.past {
          background: #f1f5f9;
          color: #94a3b8;
        }
        .nums-cell.past .value {
          color: #94a3b8;
        }
        .dp-cell.computed {
          background: #f0fdf4;
          border-color: #4ade80;
        }
        .dp-cell.active {
          border-color: #f59e0b;
          background: #fef3c7;
          transform: scale(1.08);
          box-shadow: 0 0 12px rgba(245, 158, 11, 0.35);
          z-index: 2;
        }
        .dp-cell.empty {
          background: #fafafa;
          border-style: dashed;
          border-color: #d1d5db;
          color: #9ca3af;
        }
        .explanation {
          background: #f8fafc;
          padding: 14px 16px;
          border-radius: 8px;
          font-size: 0.95rem;
          line-height: 1.6;
          margin-top: 16px;
          border-left: 4px solid #3b82f6;
        }
        @media (max-width: 640px) {
          .cell {
            width: 52px;
            min-width: 52px;
            padding: 6px 4px;
          }
          .cell .value {
            font-size: 1.05rem;
          }
          .cell .index {
            font-size: 0.6rem;
          }
          .array-row {
            gap: 6px;
            margin-bottom: 8px;
          }
          .row-label {
            min-width: 42px;
            font-size: 0.85rem;
          }
        }
      `}</style>
    </div>
  );
}