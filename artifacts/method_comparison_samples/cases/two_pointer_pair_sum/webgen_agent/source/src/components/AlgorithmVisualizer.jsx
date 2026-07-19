import React from 'react';

export default function AlgorithmVisualizer({ nums, target, left, right, sum, foundIndices, step, totalSteps, isComplete }) {
  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: 8, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
        价格列表 (升序)  |  target = <strong>{target}</strong>
      </div>
      <div className="array-viz">
        {nums.map((val, idx) => {
          let classes = 'array-value';
          if (foundIndices && (idx === foundIndices[0] || idx === foundIndices[1])) {
            classes += ' found';
          } else if (idx === left && idx === right) {
            classes += ' active-left active-right';
          } else if (idx === left) {
            classes += ' active-left';
          } else if (idx === right) {
            classes += ' active-right';
          }
          return (
            <div className="array-cell" key={idx}>
              {(idx === left || idx === right) && (
                <span className={`pointer-label ${idx === left ? 'left' : 'right'}`}>
                  {idx === left ? 'L' : 'R'}
                  {idx === left && idx === right ? ' L&R' : ''}
                </span>
              )}
              {idx !== left && idx !== right && <span className="pointer-label" style={{ visibility: 'hidden' }}>·</span>}
              <div className={classes}>{val}</div>
              <div className="array-index">[{idx}]</div>
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 8, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
        <span>🔵 L (左指针) = index {left}</span>
        <span>🔷 R (右指针) = index {right}</span>
      </div>
    </div>
  );
}