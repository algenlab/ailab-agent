import React from 'react';

export default function DpSummaryTable({ steps, currentStepIndex, nums }) {
  if (!nums || nums.length === 0) return null;

  const n = nums.length;

  return (
    <div className="dp-summary">
      <h3>DP State Transitions</h3>
      <div className="dp-table-scroll">
        <table className="dp-table">
          <thead>
            <tr>
              <th>Step</th>
              <th>House i</th>
              <th>nums[i]</th>
              {nums.map((_, idx) => (
                <th key={idx} className={idx <= currentStepIndex ? 'computed-col' : 'future-col'}>
                  dp[{idx}]
                </th>
              ))}
              <th>Recurrence Decision</th>
            </tr>
          </thead>
          <tbody>
            {steps.map((step, stepIdx) => (
              <tr key={stepIdx} className={`${stepIdx === currentStepIndex ? 'current-row' : ''} ${stepIdx < currentStepIndex ? 'past-row' : ''}`}>
                <td className="step-num">{stepIdx + 1}</td>
                <td className="house-idx">{step.houseIndex}</td>
                <td className="nums-val">{step.nums[step.houseIndex]}</td>
                {Array.from({ length: n }).map((_, colIdx) => {
                  const val = step.dp[colIdx];
                  const isComputed = val !== undefined;
                  const isCurrentCell = colIdx === step.houseIndex && stepIdx === currentStepIndex;
                  return (
                    <td key={colIdx} className={`dp-val ${isComputed ? 'filled' : 'empty'} ${isCurrentCell ? 'highlight' : ''}`}>
                      {isComputed ? val : '—'}
                    </td>
                  );
                })}
                <td className="decision-cell">
                  {step.houseIndex === 0
                    ? `dp[0] = nums[0] = ${step.dp[0]}`
                    : step.houseIndex === 1
                      ? `dp[1] = max(nums[0], nums[1]) = ${step.dp[1]}`
                      : `dp[${step.houseIndex}] = max(dp[${step.houseIndex - 1}], dp[${step.houseIndex - 2}] + nums[${step.houseIndex}]) = ${step.dpCurrentValue}`
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <style>{`
        .dp-summary {
          margin-top: 24px;
          border-top: 2px solid #e2e8f0;
          padding-top: 20px;
        }
        .dp-summary h3 {
          font-size: 1.15rem;
          margin-bottom: 12px;
        }
        .dp-table-scroll {
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
        }
        .dp-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.85rem;
          font-family: monospace;
          min-width: 600px;
        }
        .dp-table th,
        .dp-table td {
          border: 1px solid #e2e8f0;
          padding: 8px 10px;
          text-align: center;
          white-space: nowrap;
        }
        .dp-table thead th {
          background: #f1f5f9;
          font-weight: 700;
          color: #334155;
          position: sticky;
          top: 0;
        }
        .dp-table thead th.computed-col {
          background: #dcfce7;
          color: #166534;
        }
        .dp-table thead th.future-col {
          background: #f8fafc;
          color: #94a3b8;
        }
        .dp-table tbody tr.past-row {
          background: #f9fafb;
          color: #64748b;
        }
        .dp-table tbody tr.current-row {
          background: #fef3c7;
          font-weight: 600;
        }
        .dp-table tbody tr.current-row td {
          border-color: #f59e0b;
        }
        .dp-table td.dp-val.filled {
          color: #166534;
        }
        .dp-table td.dp-val.empty {
          color: #cbd5e1;
        }
        .dp-table td.dp-val.highlight {
          background: #fbbf24;
          color: #1e293b;
          font-weight: 700;
          box-shadow: inset 0 0 0 2px #f59e0b;
        }
        .dp-table td.step-num {
          font-weight: 700;
          color: #1e293b;
        }
        .dp-table td.house-idx {
          color: #3b82f6;
        }
        .dp-table td.decision-cell {
          text-align: left;
          font-size: 0.8rem;
          color: #475569;
          max-width: 300px;
          white-space: normal;
        }
        @media (max-width: 640px) {
          .dp-table {
            font-size: 0.75rem;
          }
          .dp-table th,
          .dp-table td {
            padding: 5px 6px;
          }
          .dp-table td.decision-cell {
            max-width: 180px;
          }
        }
      `}</style>
    </div>
  );
}