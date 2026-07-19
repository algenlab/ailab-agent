import React from 'react';

export default function DpTable({ steps, currentStepIndex }) {
  const computedNodes = [];
  const seen = new Set();
  for (let i = 1; i <= currentStepIndex; i++) {
    const step = steps[i];
    if (step && step.type === 'compute' && !seen.has(step.nodeId)) {
      seen.add(step.nodeId);
      computedNodes.push({
        id: step.nodeId,
        value: step.nodeValue,
        dpTake: step.dpTake,
        dpSkip: step.dpSkip
      });
    }
  }

  const currentProcessing = steps[currentStepIndex]?.currentProcessing || null;

  return (
    <table className="dp-table">
      <thead>
        <tr>
          <th>Node</th>
          <th>Value</th>
          <th>dp_take</th>
          <th>dp_skip</th>
        </tr>
      </thead>
      <tbody>
        {computedNodes.map(node => {
          const isCurrent = node.id === currentProcessing;
          return (
            <tr key={node.id} className={isCurrent ? 'current-row' : 'computed-row'}>
              <td>{node.id}</td>
              <td>{node.value}</td>
              <td>{node.dpTake}</td>
              <td>{node.dpSkip}</td>
            </tr>
          );
        })}
        {computedNodes.length === 0 && (
          <tr>
            <td colSpan={4} style={{ color: '#94a3b8', padding: '16px', textAlign: 'center', fontSize: '0.85rem' }}>
              No nodes computed yet
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}