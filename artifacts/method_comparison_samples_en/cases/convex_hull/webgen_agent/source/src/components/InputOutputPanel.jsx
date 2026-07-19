import React from 'react';

function formatPoints(pts) {
  return '[' + pts.map((p) => `[${p[0]}, ${p[1]}]`).join(', ') + ']';
}

export default function InputOutputPanel({ inputPoints, sortedPoints, expectedOutput, currentTrace }) {
  return (
    <div className="io-panel">
      <div className="io-block">
        <div className="io-label">
          <span className="io-badge input">Input</span> Delivery Points
        </div>
        <div className="io-value">{formatPoints(inputPoints)}</div>
      </div>
      <div className="io-block">
        <div className="io-label">
          <span className="io-badge sorted">Sorted</span> Lexicographic Order
        </div>
        <div className="io-value">{formatPoints(sortedPoints)}</div>
      </div>
      <div className="io-block">
        <div className="io-label">
          <span className="io-badge expected">Expected</span> Convex Hull
        </div>
        <div className="io-value">{formatPoints(expectedOutput)}</div>
      </div>
      {/* Runtime state summary */}
      {(currentTrace.lowerHull.length > 0 || currentTrace.upperHull.length > 0) && (
        <div className="io-block">
          <div className="io-label">
            <span className="io-badge lower">Lower Hull</span> Current
          </div>
          <div className="io-value">{formatPoints(currentTrace.lowerHull) || '[]'}</div>
        </div>
      )}
      {currentTrace.upperHull.length > 0 && (
        <div className="io-block">
          <div className="io-label">
            <span className="io-badge upper">Upper Hull</span> Current
          </div>
          <div className="io-value">{formatPoints(currentTrace.upperHull)}</div>
        </div>
      )}
      {currentTrace.finalHull && (
        <div className="io-block">
          <div className="io-label">
            <span className="io-badge final">Result</span> Final Hull
          </div>
          <div className="io-value">{formatPoints(currentTrace.finalHull)}</div>
        </div>
      )}
    </div>
  );
}