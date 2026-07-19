import React from 'react';
import { AlgorithmStep } from '../types';

interface Props {
  step: AlgorithmStep;
}

const StatePanel: React.FC<Props> = ({ step }) => {
  const nodes = Object.keys(step.distances);

  return (
    <div>
      {/* Distances */}
      <div className="state-section">
        <h4>📏 当前距离</h4>
        <div className="distance-grid">
          {nodes.map((node) => {
            const dist = step.distances[node];
            const distVal = typeof dist === 'number' ? dist : Infinity;
            const isVisited = step.visited.includes(node);
            const isCurrent = step.poppedNode === node && !step.isFinal;

            let cellClass = 'distance-cell';
            if (isCurrent) cellClass += ' current-cell';
            else if (isVisited) cellClass += ' visited-cell';

            const wasUpdated = step.relaxedEdges.some(
              (re) => re.to === node && re.updated
            );
            if (wasUpdated && !isCurrent && !isVisited) cellClass += ' updated';

            const displayDist =
              distVal === Infinity ? '∞' : String(distVal);

            return (
              <div key={node} className={cellClass}>
                <div className="node-name">{node}</div>
                <div className="node-dist">{displayDist}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Heap */}
      <div className="state-section">
        <h4>📦 最小堆</h4>
        <div
          className={`heap-display ${
            step.heapBefore.length === 0 && step.heapAfter.length === 0 ? 'empty' : ''
          }`}
        >
          {step.heapBefore.length === 0 &&
          step.heapAfter.length === 0 ? (
            '堆为空'
          ) : (
            <>
              {step.heapBefore.map(([d, n], i) => (
                <span key={`before-${i}`} className="heap-item">
                  ({d}, "{n}")
                </span>
              ))}
            </>
          )}
        </div>
      </div>

      {/* Visited */}
      <div className="state-section">
        <h4>✅ 已访问节点</h4>
        <div className="visited-list">
          {step.visited.length === 0 ? (
            <span style={{ color: 'var(--text-muted)', fontSize: '0.84rem' }}>
              暂无
            </span>
          ) : (
            step.visited.map((node) => (
              <span key={node} className="visited-badge">
                {node}
              </span>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default StatePanel;
